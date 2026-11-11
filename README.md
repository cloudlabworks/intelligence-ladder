# Intelligence ladder

A small, frozen, behaviourally graded coding benchmark that asks one question: **how far up a ladder of
harder task families does a model climb, and how consistently?** It compares hosted API models with a
4B model on an owned edge NPU node, using one protocol, one evaluator, and no LLM judges.

| Rung | Family | What passing requires |
|---|---|---|
| R1 | Simple functions | Correct single function against hidden asserts |
| R2 | Edge cases / Unicode / nonmutation | Correct boundary, Unicode and no-mutation behaviour |
| R3 | Three-file package repairs | JSON patch of full-file replacements that fixes a small package |
| R4 | Tool-mediated debugging | Request the exact simulated `read` calls, then patch, then report the calls made |
| R5 | Bounded two-turn revisions | Pass turn 1, then revise to a changed spec that must reject the old behaviour |
| R6 | Implementation plus self-authored mutation tests | Code passes hidden tests, own tests pass on the reference, and kill at least 4 of 5 planted mutants |
| R7 | Multi-file package feature | Change all three required source files of a five-file package; existing and hidden feature tests green |

Each rung has 4 tasks. Each task runs **3 productive repeats and 3 trap repeats** (an impossible variant
whose only correct answer is `UNKNOWN`). A task is **solved** when at least 2 of 3 productive repeats pass.
Traps never rescue a failed productive task. Temperature 0 throughout.

## Leaderboard

Full table with tokens and latency: [`results/leaderboard.md`](results/leaderboard.md)
(CSV: [`results/leaderboard.csv`](results/leaderboard.csv)). Summary:

| Model | Route / hardware class | Tasks solved (of 28) | 95% CI | Productive pass rate | Ladder height |
|---|---|---:|---|---:|---:|
| openai/gpt-6-astra (`astra`) | hosted API (OpenRouter) | 28 | [28, 28] | 0.988 | 7 |
| qwen-plus | hosted API (Alibaba Cloud Model Studio) | 19 of 23 run | [15, 22] | 0.866 | 3 |
| deepseek/deepseek-v4-flash | hosted API (OpenRouter) | 19 | [14, 24] | 0.667 | 1 |
| qwen-flash | hosted API (Alibaba Cloud Model Studio) | 17 | [12, 22] | 0.595 | 1 |
| Qwen3-4B-Instruct-2507 W8A8 (`RK1-Qwen3-4B`) | owned edge SoC: Turing RK1, RK3588 NPU | 7 | [3, 12] | 0.250 | 1 |
| qwen/qwen3.7-flash | hosted API (OpenRouter) | 1 | [0, 3] | 0.048 | 0 |
| z-ai/glm-4.7-flash | hosted API (OpenRouter) | 1 | [0, 3] | 0.036 | 0 |
| openai/gpt-5-nano | hosted API (OpenRouter) | 0 | [0, 0] | 0.012 | 0 |

CI: cluster bootstrap over whole tasks (4000 resamples, seed 20261110). Ladder height: highest rung *n*
with every family R1..R*n* eligible (all four tasks solved). `qwen-plus` stopped during R6 and R7 was not
run; missing trials are not failures.

### Read these numbers carefully

- **Different resource caps.** Hosted routes had a 2048-token output cap on R6/R7 (512 on R1–R5). The RK1
  edge node kept its native 512-token output and 2048-token context limits on every rung. Its R6/R7 zeros
  partly reflect that cap.
- **Reasoning eats the output cap.** Turns that hit the output cap with every completion token spent on
  reasoning (so no answer text): qwen3.7-flash 109 of 183, gpt-5-nano 82 of 182, glm-4.7-flash 49 of 180
  (104 of 180 hit the cap), deepseek-v4-flash 28 of 192, astra 0 of 191. The ladder measures what a model
  returns under a fixed cap, not its unconstrained ceiling.
- **Three repeats measure consistency, not broad reliability.** 28 tasks is small; the intervals are wide.
- **Latency instruments differ by route**: streaming first-content event (OpenRouter), buffered wall time
  (Model Studio), native NPU runtime counters (RK1). Trial wall time includes transport and scoring.
- **Power was not metered** on any route, so this release reports no energy figures.
- **Hosted hardware is not disclosed** by the providers, so hosted rows carry no hardware class beyond
  "hosted API".

## Reproduce

```bash
./reproduce.sh            # sha256 check of every package file, then python3 reproduce.py
python3 reproduce.py      # standard library only, Python 3.9+
```

`reproduce.py`:

1. Verifies the two freeze manifests (`frozen/SHA256SUMS.json`, sha256 `311c38c0…`, used for R6/R7 and the
   later sweeps; `frozen/history/R1-R5-SHA256SUMS.json`, sha256 `62cee420…`, used for the first R1–R5
   runs) against the shipped frozen files, and confirms the withheld entries are absent
   ([`frozen/WITHHELD.md`](frozen/WITHHELD.md)).
2. Checks every row's `freeze_sha256` is one of those two manifests.
3. Recomputes the capability profile and R6 component tables from `data/results.jsonl` and requires an
   exact line match with [`reference/RESULTS-reference.md`](reference/RESULTS-reference.md), the tables the
   original harness produced.
4. Recomputes the leaderboard and requires it to equal `results/leaderboard.{md,csv}`.

`python3 reproduce.py --write` regenerates the leaderboard files after you add results.

Smoke tests (Space table build, Gradio UI construction without launch, harness against a local mock
server with a negative control): `python3 tests/smoke_test.py` (needs `pytest`; `gradio` optional).

## Layout

| Path | Contents |
|---|---|
| `data/results.jsonl` | 1309 per-trial rows: pass/fail, structural score fields, tokens, latency |
| `data/models.json` | Result label → model ref, route, hardware class, output caps, latency instrument |
| `frozen/` | Byte-identical frozen tasks (`rungs/R1–R7.json`), prompts, evaluators, protocol, manifests |
| `reference/` | Tables from the original run report, for the exact-match check |
| `results/` | Generated leaderboard (Markdown and CSV) |
| `ladder.py` | Scoring and leaderboard logic shared by `reproduce.py` and `app.py` |
| `app.py`, `requirements.txt`, `space/README.md` | Gradio leaderboard Space; reads only `data/` |
| `harness/run_model.py` | Public runner for any OpenAI-compatible endpoint |
| `DATASET_CARD.md` | Hugging Face dataset card |

## What the per-trial data keeps and drops

Kept: trial id, task, rung, repeat, trap flag, model label, freeze manifest hash, pass/fail and structural
score fields (return codes, tool-call exactness, mutant kills, changed paths, harness rejection messages),
prompt/completion/reasoning token counts, wall time, TTFT, tok/s and the instrument that produced them.

Dropped: provider account-usage fields, raw pytest logs and evaluator tracebacks (they contain local paths), and
model answer text. The evaluator re-scoring of three early `astra` R1 rows (the original interpreter lacked
pytest; the same saved answers were re-scored with the frozen evaluator, no new model call) is recorded in
their `evaluation_repair` field.

## Licences

Code (`*.py`, `*.sh`): [MIT](LICENSE). Data, task files and documentation: [CC BY 4.0](DATA_LICENSE.md).

## Adding a model

See [CONTRIBUTING.md](CONTRIBUTING.md).
