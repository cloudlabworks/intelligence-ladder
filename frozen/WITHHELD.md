# Withheld frozen files

`SHA256SUMS.json` lists 41 frozen files. This release ships 12 of them byte-identical. The other 29 are
withheld on purpose; their sha256 values stay in the manifest, so the manifest hash recorded on every
result row (`freeze_sha256`) is unchanged and a later release of these files can be verified against it.

| Withheld | Count | Why |
|---|---:|---|
| `hidden/R1-A.json` … `hidden/R7-D.json` | 28 | Reserved held-out variants. Never executed in any run. Kept private so they can later test whether a model's ladder score survives on unseen variants of the public tasks. |
| `runner.py` | 1 | The original site-specific runner. It carries deployment defaults for the original lab and two adapters that only work there. Its trial loop is reproduced unchanged in `harness/run_model.py`. |

`history/R1-R5-SHA256SUMS.json` is the earlier manifest (sha256 `62cee420…`) that the first `astra` and
`RK1-Qwen3-4B` R1–R5 runs used. It covers 28 files: 20 reserved variants (withheld), 7 files identical to
the current ones, and `protocol.json` version 1, shipped as `history/R1-R5-protocol.json`. The only
protocol change between versions added the R6/R7 extension fields; R1–R5 tasks, prompts and evaluator are
byte-identical across both manifests.

`references.json` (reference solutions for R1–R5, used by the original self-test) is not in either
manifest; it is covered by the package `SHA256SUMS`.
