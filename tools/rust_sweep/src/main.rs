// rust_sweep — the wide arm in Rust. No index, no ranking, no extension filter.
//
// The same tool as `tools/wide_sweep.py`, for corpora where the Python walk is too slow to run
// unconditionally. Read that file's header first: it explains WHY a deliberately worse search
// belongs in the box, and that reasoning is the whole point. This file is the fast implementation
// of it, not a different idea.
//
//     cargo run --release -- --roots ../../memory -- cache locale
//     cargo run --release -- cache locale            # defaults to the repo's memory/ dir
//
// ⚠ The default root used to be the literal relative path "../../memory", correct only when run
//   from tools/rust_sweep/. Run the built binary from the repo root and it searched nothing and
//   said so, which is the exact silent-scope failure this file warns about four lines below. It
//   now resolves against the executable's own location, matching the Python arm's absolute default.
//
// ⚠⚠⚠ SEMANTICS MUST MIRROR wide_sweep.py EXACTLY, or a comparison between the two silently
//   credits the language with a scoping difference and calls it speed.
//   ★ THIS CLAIM WAS FALSE WHEN FIRST PUBLISHED. Verified by one query on a corpus with no ties,
//     no generated files, no symlinks and nothing outside cp1252 — every dimension where the arms
//     diverged was absent, so the check could not fail. Now enforced by tools/sweep_conformance.py
//     against a fixture built to contain exactly those cases. Do not re-assert it by reading.
//   The pinned rules:
//     * walk the same roots
//     * skip the same directory names (dependency trees, not file types)
//     * binary = magic prefix OR a NUL byte in the first 1024 bytes
//     * HEAD FIRST, then the rest — this is the whole performance story, see below
//     * a file matches only if EVERY term is present (AND, not OR), case-insensitive
//     * order authored-above-generated, then by hit DENSITY, then raw count, then path
//   If you change a matching rule here, change it there in the same commit. A drifted pair is
//   worse than one arm, because it produces a number that looks like a language comparison.
//
// ⚠ NO EXTENSION WHITELIST. That is the defect this tool exists to avoid, and it is the first
//   thing anyone adds to make a full sweep affordable. An extension list is a scope decision made
//   once, invisible at query time, and reported to you as absence — which is the exact failure the
//   ranked path already has. Do not reintroduce it here.

use std::env;
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;

// ⚠ PINNED TO wide_sweep.py's SKIP_DIRS. Same list, same order, same reason.
const SKIP_DIRS: [&str; 7] = [
    "venv", ".venv", "site-packages", "node_modules", ".git", "__pycache__", "target",
];
const MAGIC: [&[u8]; 9] = [
    b"\x89PNG", b"RIFF", b"ID3", b"\xff\xd8\xff", b"PK\x03\x04", b"OggS", b"MZ", b"\x7fELF",
    b"\x1f\x8b",
];
const MAX_BYTES: u64 = 64_000_000;
const HEAD: usize = 2048;

/// Did one of your own tools write this, rather than you?
///
/// ⚠⚠ LABEL, DO NOT REMOVE. The sweep's entire virtue is that it excludes nothing — that is why it
///   finds what an index cannot — so adding an exclusion to fix a DISPLAY problem trades away the
///   one property it has. "What did my index actually hold for X" is a real question, and dropping
///   generated files to tidy the output makes it permanently unanswerable. These sort BELOW
///   authored files and carry a tag; nothing is ever dropped.
///
/// ⚠ THE PATTERN LIST IS INTERIM AND WILL ROT. The durable version is that every generator writes
///   a sidecar beside its output and this reads the sidecar instead of guessing from the name. The
///   sidecar check is first so it wins as generators adopt it.
fn is_generated(p: &Path) -> bool {
    let name = p
        .file_name()
        .map(|n| n.to_string_lossy().to_lowercase())
        .unwrap_or_default();
    let mut side = p.to_path_buf();
    side.set_extension("freshness.json");
    if side.exists() {
        return true;
    }
    name.contains("_meta")
        || name.contains("corpus_index")
        || name.contains("_disagreements")
        || name.ends_with(".freshness.json")
        || name.contains("_index_meta")
}

fn looks_binary(head: &[u8]) -> bool {
    for m in MAGIC.iter() {
        if head.starts_with(m) {
            return true;
        }
    }
    head.iter().take(1024).any(|&b| b == 0)
}

/// Case-insensitive ASCII substring search over raw bytes. No decoding: the file never becomes a
/// String, which is what makes this cheap and is also why the match is byte-exact rather than
/// approximate. Non-ASCII text still matches on its exact bytes.
fn contains_ci(hay: &[u8], needle: &[u8]) -> bool {
    if needle.is_empty() || hay.len() < needle.len() {
        return false;
    }
    let first = needle[0].to_ascii_lowercase();
    for i in 0..=(hay.len() - needle.len()) {
        if hay[i].to_ascii_lowercase() != first {
            continue;
        }
        if hay[i..i + needle.len()]
            .iter()
            .zip(needle.iter())
            .all(|(a, b)| a.to_ascii_lowercase() == b.to_ascii_lowercase())
        {
            return true;
        }
    }
    false
}

fn count_ci(hay: &[u8], needle: &[u8]) -> usize {
    if needle.is_empty() || hay.len() < needle.len() {
        return 0;
    }
    let mut n = 0;
    let mut i = 0;
    while i + needle.len() <= hay.len() {
        if hay[i..i + needle.len()]
            .iter()
            .zip(needle.iter())
            .all(|(a, b)| a.to_ascii_lowercase() == b.to_ascii_lowercase())
        {
            n += 1;
            i += needle.len();
        } else {
            i += 1;
        }
    }
    n
}

fn collect(root: &Path, out: &mut Vec<PathBuf>) {
    let rd = match std::fs::read_dir(root) {
        Ok(r) => r,
        Err(_) => return,
    };
    for e in rd.flatten() {
        let p = e.path();
        // ⚠⚠⚠ USE metadata(), NOT file_type(). DirEntry::file_type does NOT resolve reparse
        //   points, so a junction or symlink is neither is_dir nor is_file, fell into the empty
        //   match arm, and was DROPPED SILENTLY AND UNCOUNTED. Python's os.walk descends into
        //   them. A tool whose stated purpose is catching SCOPE errors had a silent scope hole of
        //   its own, in the arm recommended for large corpora. metadata() follows the link.
        let md = match std::fs::metadata(&p) {
            Ok(m) => m,
            Err(_) => continue,
        };
        if md.is_dir() {
            let name = e.file_name();
            let name = name.to_string_lossy();
            if !SKIP_DIRS.iter().any(|s| *s == name) {
                collect(&p, out);
            }
        } else if md.is_file() {
            out.push(p);
        }
    }
}

fn main() {
    // ⚠ ROOTS COME FROM THE CALLER. A hard-coded absolute path makes the tool search NOTHING on
    //   anyone else's machine and report it as no matches — which is the exact silent-scope failure
    //   this whole tool exists to expose. Refusing to guess is cheaper than debugging that later.
    let argv: Vec<String> = env::args().skip(1).collect();
    let mut roots: Vec<PathBuf> = Vec::new();
    let mut terms_raw: Vec<String> = Vec::new();
    let mut limit: usize = 8;
    // ⚠⚠⚠ THE PREVIOUS LOOP WAS STICKY AND IT INVENTED A DIRECTORY. `in_roots` was set by --roots
    //   and cleared ONLY by `--`, so an unrecognised flag fell through to the term arm WITHOUT
    //   clearing it and the next value was eaten as a root:
    //       --roots ./sample --limit 3 -- the
    //   parsed as terms=["--limit"], roots=["./sample","3"], and then printed my own carefully
    //   written "root does not exist" warning about a directory the PARSER had fabricated. The
    //   guard fired correctly on a fault its own caller caused, which is the most misleading
    //   possible output: a real alarm about an unreal thing.
    //   ⚠ It also did not honour `--` as end-of-options, contradicting the usage string above, so
    //     a search term could never literally be "--roots" or "--".
    let mut mode_roots = false;      // consuming values for --roots
    let mut end_of_opts = false;     // everything after `--` is a term, full stop
    let mut i = 0;
    while i < argv.len() {
        let a = argv[i].as_str();
        if !end_of_opts && a == "--" {
            end_of_opts = true;
            mode_roots = false;
        } else if !end_of_opts && a == "--roots" {
            mode_roots = true;
        } else if !end_of_opts && a == "--limit" {
            mode_roots = false;
            i += 1;
            match argv.get(i).and_then(|v| v.parse::<usize>().ok()) {
                Some(n) => limit = n,
                None => {
                    eprintln!("rust_sweep: --limit needs a number");
                    std::process::exit(1);
                }
            }
        } else if !end_of_opts && a.starts_with("--") {
            // ⚠ REFUSE, do not absorb. Silently treating an unknown flag as a search term is how
            //   a typo becomes a query and returns a confident zero.
            eprintln!("rust_sweep: unknown option {}  (use `--` before terms starting with --)", a);
            std::process::exit(1);
        } else if mode_roots {
            roots.push(PathBuf::from(a));
        } else {
            terms_raw.push(a.to_string());
        }
        i += 1;
    }
    if roots.is_empty() {
        // ⚠ RESOLVE AGAINST THIS FILE, NOT THE CWD. The old default "../../memory" is correct only
        //   when run from tools/rust_sweep/ -- run the built binary from the repo root and it
        //   searched nothing, which is the exact silent-scope failure warned about two lines below.
        //   Python's DEFAULT_ROOTS is absolute; "walk the same roots" was false by default.
        let mut d = env::current_exe().unwrap_or_else(|_| PathBuf::from("."));
        for _ in 0..4 {            // target/release/rust_sweep.exe -> tools/rust_sweep -> tools -> repo
            d.pop();
        }
        d.push("memory");
        roots.push(d);
    }
    // ⚠ BLANK TERMS: Python filters on t.strip(); this did not, so `"" badger` returned 0 matches
    //   in Rust and 3 in Python, and `" " badger` returned the SAME COUNT with different hit
    //   totals -- agreement on the headline, divergence in the ranking underneath it.
    terms_raw.retain(|t| !t.trim().is_empty());
    if terms_raw.is_empty() {
        eprintln!("usage: rust_sweep [--roots DIR ...] [--limit N] [--] <term> [term ...]");
        eprintln!("       AND across terms, case-insensitive, no index, no extension filter");
        std::process::exit(1);
    }
    let missing: Vec<&PathBuf> = roots.iter().filter(|r| !r.is_dir()).collect();
    if !missing.is_empty() {
        // ⚠ SAY IT. A root that does not exist yields zero matches, which is indistinguishable from
        //   a corpus that does not contain the term. Never let those two share an output.
        eprintln!("rust_sweep: WARNING — {} root(s) do not exist and were skipped:", missing.len());
        for m in &missing {
            eprintln!("    {}", m.display());
        }
        eprintln!("  A missing root returns no matches, which reads exactly like an absent term.");
    }
    let terms: Vec<Vec<u8>> = terms_raw.iter().map(|s| s.as_bytes().to_vec()).collect();

    let t0 = Instant::now();
    let mut files = Vec::new();
    for r in &roots {
        collect(r, &mut files);
    }
    let walk_ms = t0.elapsed().as_millis();

    let files = Arc::new(files);
    let idx = Arc::new(AtomicUsize::new(0));
    let scanned = Arc::new(AtomicUsize::new(0));
    let binary = Arc::new(AtomicUsize::new(0));
    let toobig = Arc::new(AtomicUsize::new(0));
    let hits: Arc<Mutex<Vec<(bool, usize, usize, PathBuf)>>> = Arc::new(Mutex::new(Vec::new()));

    let nthreads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);
    let mut handles = Vec::new();
    for _ in 0..nthreads {
        let files = Arc::clone(&files);
        let idx = Arc::clone(&idx);
        let scanned = Arc::clone(&scanned);
        let binary = Arc::clone(&binary);
        let toobig = Arc::clone(&toobig);
        let hits = Arc::clone(&hits);
        let terms = terms.clone();
        handles.push(std::thread::spawn(move || {
            let mut head = vec![0u8; HEAD];
            loop {
                let i = idx.fetch_add(1, Ordering::Relaxed);
                if i >= files.len() {
                    break;
                }
                let p = &files[i];
                let meta = match std::fs::metadata(p) {
                    Ok(m) => m,
                    Err(_) => continue,
                };
                if meta.len() > MAX_BYTES {
                    toobig.fetch_add(1, Ordering::Relaxed);
                    continue;
                }
                let mut f = match File::open(p) {
                    Ok(f) => f,
                    Err(_) => continue,
                };
                // ⚠⚠ HEAD FIRST, THEN THE REST — the single most important ordering in this file.
                //    Reading the whole file and THEN asking whether it was binary loads every media
                //    file and archive on the machine in full before discarding it. The binary check
                //    exists in that version too; it simply runs too late to save anything. Cost is
                //    decided by where this check sits, not by which files you skip.
                let n = match f.read(&mut head) {
                    Ok(n) => n,
                    Err(_) => continue,
                };
                if looks_binary(&head[..n]) {
                    binary.fetch_add(1, Ordering::Relaxed);
                    continue;
                }
                let mut data = Vec::with_capacity(meta.len() as usize + 1);
                data.extend_from_slice(&head[..n]);
                if f.read_to_end(&mut data).is_err() {
                    continue;
                }
                scanned.fetch_add(1, Ordering::Relaxed);
                // prefilter on the first term: an AND search requires it anyway, so this is a pure
                // speedup with no effect on results.
                if !contains_ci(&data, &terms[0]) {
                    continue;
                }
                if terms.iter().all(|t| contains_ci(&data, t)) {
                    let total: usize = terms.iter().map(|t| count_ci(&data, t)).sum();
                    // ⚠ DENSITY, NOT RAW COUNT. Raw count means the biggest file always wins, and
                    //   the biggest file in a memory system is usually an index dump holding a copy
                    //   of everything — so searching it for an answer is circular, and it outranks
                    //   every note you actually wrote. Hits per KB puts a short note above a huge
                    //   dump. It is NOT a filter: nothing is excluded, so the sweep keeps the one
                    //   property it exists for. Scaled by 1000 to stay in integers.
                    let kb = std::cmp::max(1, data.len() / 1024);
                    let density = total * 1000 / kb;
                    let gen = is_generated(p);
                    hits.lock().unwrap().push((gen, density, total, p.clone()));
                }
            }
        }));
    }
    for h in handles {
        h.join().ok();
    }

    let mut hits = hits.lock().unwrap().clone();
    hits.sort_by(|a, b| {
        a.0.cmp(&b.0)
            .then(b.1.cmp(&a.1))
            .then(b.2.cmp(&a.2))
            // ⚠⚠ STRING COMPARE, NOT PathBuf. PathBuf's Ord is COMPONENT-WISE and never sees the
            //   separator, so "T.md" vs "T\z.md" orders opposite to Python's byte-wise
            //   string compare. With tied hits and density that silently returns a DIFFERENT
            //   document under an 8-item limit -- same query, same corpus, different answer.
            .then(a.3.to_string_lossy().cmp(&b.3.to_string_lossy()))
    });
    let ms = t0.elapsed().as_millis();
    // ⚠ MATCHED AND SHOWN ARE DIFFERENT NUMBERS. Printing the length of a truncated list as the
    //   headline makes it read as "found" while meaning "shown" — a count that means something
    //   narrower than it says will be read as the wider thing every time.
    let shown = std::cmp::min(limit, hits.len());
    println!(
        "rust_sweep: {} matched ({} shown) | {} scanned, {} binary, {} toobig | walk {}ms, total {}ms, {} threads  [UNRANKED — density, not relevance]",
        hits.len(),
        shown,
        scanned.load(Ordering::Relaxed),
        binary.load(Ordering::Relaxed),
        toobig.load(Ordering::Relaxed),
        walk_ms,
        ms,
        nthreads
    );
    let none = hits.is_empty();
    for (g, d, n, p) in hits.iter().take(shown) {
        println!(
            "  {} x{:<5} d{:<5} {}",
            if *g { "[gen]" } else { "     " },
            n,
            d,
            p.display()
        );
    }
    // ⚠ SAME EXIT CODE AS THE PYTHON ARM. They diverged (2 vs always-0), so any script branching
    //   on "did the sweep find anything" behaved differently depending on which arm it called.
    if none {
        std::process::exit(2);
    }
}
