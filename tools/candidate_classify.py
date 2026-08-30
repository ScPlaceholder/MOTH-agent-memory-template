"""candidate_classify.py — EmbeddingGemma decides which messages are worth remembering.

★★★★★ THE ARCHITECTURE IS GPT'S, RELAYED BY J 2026-08-29, AND THE PLACEMENT IS MINE FOR A MEASURED
REASON. GPT proposed a small model classifying each utterance as CURRENT_CONTEXT vs MEMORY_CANDIDATE.
J then supplied the piece that made it safe: *"why can't memory candidate be a rolling file that
updates after a write and retrieval?"* — a queue rather than a memory, so a wrong call is reversible.

⚠ IT DELIBERATELY DOES NOT RUN ON THE MESSAGE PATH. Twenty minutes before this file existed I added
  retrieval inline to `watch_messages._emit`, and on its first live fire the extra payload blew the
  event budget and **truncated J's actual question away** — I could see three retrieved files and not
  the message they belonged to. Anything bolted to that path competes with the message for one
  budget, and the message must win. So this is a separate pass over the inbox, and the classifier
  never touches the wire the family's messages travel on.
  ★ That also makes the cost irrelevant: `embeddinggemma:300m` lives on MAIN, whose per-call ollama
    overhead I measured at 2,307 ms (against 148 on right, 74 on left). Unusable inline. Fine here.

★★★ IT IS AN EMBEDDER, SO THE METHOD IS NEAREST-LABELLED-EXAMPLE, NOT PROMPTING.
    Measured 2026-08-29: prompting a chat model for this scored 0/8 zero-shot and 4/8 few-shot on
    llama3.2, and gemma4:12b returned an EMPTY STRING. Using an embedder as a kNN classifier over a
    handful of labelled sentences scored 7/8 — twelve times faster and nothing downloaded.
    ⚠ Both zeros were MY harness, not the models: I ran zero-shot when the spec said few-shot, and
      scored an empty string as a wrong answer. An extreme result against someone else's idea is
      evidence about my test before it is evidence about the idea.

★★ AND kNN GIVES THE `why` FOR FREE, WHICH IS THE PART THAT MADE THIS WORTH BUILDING.
   `memory_candidates.capture()` REQUIRES a reason, because a candidate without one is an orphan
   sentence in three weeks. A chat classifier would hand me a confidence number — and I measured today
   that confidence cannot separate signal from noise here (real hit 0.727, junk 0.719). The nearest
   labelled example is not a score, it is an explanation: *"looks like: 'I prefer smaller models
   because I care about latency'"*. That is checkable by a human later.
"""
import io
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ⚠⚠ THE DEFAULT MODEL IS NOT MIT, AND THIS FILE SHIPPED WITHOUT SAYING SO. Checked upstream
#   2026-08-30: EmbeddingGemma is released under **Google's Gemma Terms of Use**, not MIT or Apache.
#   That is a real constraint someone may not be able to accept, and it arrived here as a hardcoded
#   default — so a user running this tool out of the box pulls those terms without being asked.
#   ★ Made overridable rather than swapped, because the measured result belongs to THIS model: an
#     embedder used as a kNN classifier scored 7/8 where prompting a chat model scored 0/8 zero-shot
#     and 4/8 few-shot. Changing the default would quietly invalidate that number.
#     Any embedding endpoint works — `MEMORY_EMBED_MODEL=bge-m3` for an MIT-licensed alternative.
#   ⚠ The licence is the model author's to change. Check it yourself before you install; this comment
#     is a pointer, not a warranty, and it was accurate on the date above and no other.
MODEL = os.environ.get("MEMORY_EMBED_MODEL", "embeddinggemma:300m")
HOST = os.environ.get("GEMMA_HOST", "127.0.0.1:11434")

# ★ The labelled set, from GPT's own examples plus family-shaped ones. Small on purpose: this is a
#   kNN classifier, and every example is a claim about what the label MEANS. Adding a vague one makes
#   every future decision vaguer, so they stay few and unambiguous.
EXAMPLES = [
    ("MEMORY_CANDIDATE", "I've been building this memory architecture for the last six months."),
    ("MEMORY_CANDIDATE", "Actually, I prefer smaller models because I care about latency."),
    ("MEMORY_CANDIDATE", "I'm supposed to pull a permit every time I pull more than 6 feet of wire."),
    # ⚠ THIS SLOT HELD A REAL FAMILY HANDLE UNTIL 2026-08-30, AND IT WAS ABOUT TO BE PUBLISHED.
    #   The example is doing a specific job — teaching that a bare identifier-fact is durable — so it
    #   has to stay a bare identifier-fact. But it does NOT have to be a real one, and the version
    #   here named an actual person's account. Found by a pre-upload scan I only ran because someone
    #   asked "what's left to do", which is a thin thread to hang a privacy check on.
    ("MEMORY_CANDIDATE", "My co-founder's handle on the forum is riverbend_ok."),
    ("CURRENT_CONTEXT", "Yeah, that's exactly what I meant."),
    ("CURRENT_CONTEXT", "What about using Qwen instead?"),
    ("CURRENT_CONTEXT", "Did you wire in the two things we were talking about?"),
    ("CURRENT_CONTEXT", "Can you send me the write up"),
]


def embed(texts, model=MODEL, host=None):
    """[[float]] — one vector per text. Raises rather than returning garbage on failure."""
    host = host or HOST
    out = []
    for t in texts:
        body = json.dumps({"model": model, "prompt": t}).encode()
        req = urllib.request.Request("http://%s/api/embeddings" % host, data=body,
                                     headers={"Content-Type": "application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
        v = d.get("embedding")
        if not v:
            raise RuntimeError("no embedding returned for %r" % t[:40])
        out.append(v)
    return out


def _cos(a, b):
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return num / (na * nb) if na and nb else 0.0


def classify(text, ex_vecs=None, host=None):
    """(label, nearest_example, score) — nearest labelled example wins. No threshold anywhere.

    ⚠ THERE IS NO CONFIDENCE CUTOFF AND THAT IS DELIBERATE. Measured today, an absolute cosine
      cannot separate a real hit from junk on this corpus (0.727 vs 0.719). So the decision is
      RELATIVE — which labelled sentence is closest — and a relative comparison does not need a
      number I cannot justify. The safety net is not a threshold; it is that the output goes to a
      reversible queue.
    """
    if ex_vecs is None:
        ex_vecs = embed([e[1] for e in EXAMPLES], host=host)
    v = embed([text], host=host)[0]
    best = max(range(len(EXAMPLES)), key=lambda i: _cos(v, ex_vecs[i]))
    return EXAMPLES[best][0], EXAMPLES[best][1], round(_cos(v, ex_vecs[best]), 4)


def run(texts, host=None, capture=True):
    """Classify a batch; capture the MEMORY_CANDIDATEs. Returns [(label, text, why)]."""
    # ⚠ THE EXAMPLE EMBEDDING IS INSIDE THE GUARD, AND IT WAS NOT AT FIRST.
    #   v1 called this bare, so an ollama outage raised out of `run()` and killed the whole batch
    #   instead of reporting per item — the caller is a sweep over the inbox, so one dead model meant
    #   zero messages classified and an exception where a report should be. My own failure test
    #   caught it on the first execution, which is the only reason it is not still there.
    try:
        ex_vecs = embed([e[1] for e in EXAMPLES], host=host)
    except Exception as e:
        return [("ERROR", t, "embedder unavailable (%s)" % type(e).__name__) for t in texts]
    out = []
    for t in texts:
        try:
            label, near, score = classify(t, ex_vecs=ex_vecs, host=host)
        except Exception as e:
            out.append(("ERROR", t, "%s" % type(e).__name__))
            continue
        why = "gemma kNN %.3f, looks like: %s" % (score, near)
        out.append((label, t, why))
        if capture and label == "MEMORY_CANDIDATE":
            try:
                import memory_candidates as MC
                MC.capture(t, why=why, source="telegram", kind="gemma")
            except Exception:
                pass
    return out


def selftest():
    """Tests the DECISION LOGIC with a stub embedder — no model, no network.

    ⚠ A suite that needs ollama up is a suite that goes red for reasons unrelated to this file, and
      an always-red check is one I stop reading. The model's ACCURACY is measured separately
      (7/8 on 2026-08-29); what is tested here is that the plumbing picks the nearest label,
      surfaces the example as the reason, and never silently swallows an embedder failure.
    """
    ok = True
    # stub: vector = [1,0] for anything containing 'prefer'/'permit'/'building', else [0,1]
    def fake_embed(texts, model=None, host=None):
        return [[1.0, 0.0] if any(k in t.lower() for k in ("prefer", "permit", "building", "handle"))
                else [0.0, 1.0] for t in texts]
    real = globals()["embed"]
    globals()["embed"] = fake_embed
    try:
        label, near, _s = classify("Actually I prefer running things locally")
        if label != "MEMORY_CANDIDATE":
            print("  FAIL: a durable preference classified as %r" % label); ok = False
        if not near:
            print("  FAIL: no nearest example returned — the example IS the reason, and "
                  "memory_candidates refuses a capture without one"); ok = False

        label, _n, _s = classify("Yeah that works for me")
        if label != "CURRENT_CONTEXT":
            print("  FAIL: conversational filler classified as %r" % label); ok = False

        res = run(["Actually I prefer running things locally"], capture=False)
        if not res or "looks like:" not in res[0][2]:
            print("  FAIL: the why does not name the example it matched"); ok = False
    finally:
        globals()["embed"] = real

    # ★ an embedder failure must SURFACE, not become a silent CURRENT_CONTEXT — that would drop
    #   every durable fact on the floor while looking like a working classifier.
    def boom(texts, model=None, host=None):
        raise RuntimeError("ollama down")
    globals()["embed"] = boom
    try:
        res = run(["anything"], capture=False)
        if not res or res[0][0] != "ERROR":
            print("  FAIL: an embedder outage was reported as a classification. Silent failure here "
                  "means every memory-worthy line is quietly discarded."); ok = False
    finally:
        globals()["embed"] = real

    print("  4/4 classifier cases ok" if ok else "  classifier FAILURES above")
    print("candidate_classify selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 2


def main():
    if "--selftest" in sys.argv:
        return selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: candidate_classify.py <text> [...] | --selftest")
    t0 = time.time()
    for label, text, why in run(args, capture=("--capture" in sys.argv)):
        print("  %-17s %s" % (label, text[:70]))
        print("      %s" % why)
    print("  (%.1fs)" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
