# Third-party components

**This repository distributes none of them.**

That is not a disclaimer, it is the reason this file reads differently from a normal third-party
licence inventory. There are no vendored libraries and no bundled weights.

**The bound of that check, because a claim about absence is only as good as the search behind it:**
a full `os.walk` from the repository root, no depth limit and no exclusions — 8 directories, 45
files, maximum depth 2 — testing for `.bin`, `.safetensors`, `.onnx`, `.gguf`, `.pt`, `.h5`, `.npz`,
`.pkl`, `.pth`, `.tflite` and `.mlmodel`. Zero matches. The tree is small enough that the search
covers all of it, which is the only reason this can be stated as an absolute rather than a
"none found". The tools are Python
standard library only: `argparse`, `ast`, `fnmatch`, `io`, `json`, `os`, `re`, `shutil`, `sys`,
`tempfile`, `time`, `urllib`. There is no `requirements.txt` because there is nothing to require.

So this is not an inventory of what ships with the code. **It is a list of what you would be taking
on if you switch the optional tiers on**, and the obligation arrives with your download, not with
this repository.

## The optional tiers

| component | used for | licence (checked 2026-08-30) | commercial use |
|---|---|---|---|
| `BAAI/bge-m3` | dense embeddings | MIT | yes |
| `BAAI/bge-reranker-base` | cross-encoder rerank | MIT | yes |
| `nomic-embed-text` v1.5 | dense embeddings | Apache 2.0 | yes |
| NAVER SPLADE models | sparse expansion | **CC BY-NC-SA 4.0** | **NO — non-commercial** |
| EmbeddingGemma | write-side classifier | **Google Gemma Terms** | review required |

⚠ **Two of these need real attention before any commercial use.**

**SPLADE is non-commercial and share-alike.** That is a hard blocker for a commercial product
regardless of how it benchmarks — and it benchmarks well, which is exactly when a blocker gets
quietly downgraded. Stage 6 of `docs/BUILD_PROMPTS.md` also rejects it on measured grounds when fused
into the ranking, for reasons unrelated to licensing. Two independent gates, both failing.

**EmbeddingGemma is under Google's Gemma Terms**, not a conventional open-source licence. It is the
default in `tools/candidate_classify.py` and it is overridable — set `MEMORY_EMBED_MODEL` to
something else, `bge-m3` for an MIT alternative. The default was left in place because the measured
7/8 classification result belongs to that specific model, and changing it silently would invalidate
the number that justifies the design.

## The runtimes, if you use them

Not required by anything here, but commonly present when the optional tiers are enabled: PyTorch and
NumPy are BSD-3-Clause, Hugging Face Transformers and Sentence Transformers are Apache 2.0, ONNX
Runtime and FAISS are MIT.

## Two honest limits on this file

**These were checked on 2026-08-30 and licences change.** A model author can relicense at any time,
and a table in someone else's repository is not a warranty. Check the model card yourself before you
depend on it — this file is a pointer to the question, not an answer you can rely on.

**Nothing here is legal advice.** If this system is going into a product, the licence arrangement
should be reviewed by someone qualified, and the two flagged rows above are where that review should
start.

## The escape hatch

Every optional tier can be switched off. With all of them disabled the system still runs on the
keyword and keyize engines, which are original code under this repository's own licence and require
no third-party model at all. If the licensing of any component is a problem for your use, that
configuration is the answer — and it is the default.
