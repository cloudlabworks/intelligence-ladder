# Adding a model

Results are accepted only from the unchanged frozen suite. A run takes 168 trials (28 tasks x 3 productive
+ 3 trap repeats).

## 1. Run the ladder

Requirements: Python 3.9+, `pytest` in the same interpreter, an OpenAI-compatible streaming endpoint
(`/v1/chat/completions` with `stream_options.include_usage`).

```bash
python3 -m pip install pytest
export LADDER_API_KEY=...            # only if the endpoint needs a key; never pass it on the command line
python3 harness/run_model.py \
  --model ORG/MODEL --label my-model \
  --base-url http://127.0.0.1:8000/v1 \
  --out runs/my-model
```

- The runner refuses to start if any shipped frozen file differs from `frozen/SHA256SUMS.json`.
- `--resume` continues an interrupted run; model-answer failures never stop it, infrastructure errors do
  (`runs/my-model/BLOCKED.json`).
- **The evaluator executes model-written code.** On macOS it runs under `sandbox-exec` (no network, no file
  writes). On Linux it only applies rlimits, so run inside a disposable container or VM.
- Do not change temperature (0), output caps, prompts or tasks. If your route cannot meet the caps (for
  example a small edge context window), report that in `data/models.json`, as the RK1 row does.

`runs/my-model/results.jsonl` keeps everything locally, including execution logs. The publishable file is
`runs/my-model/results.public.jsonl`, the same row format as `data/results.jsonl` with logs stripped.

### Differences from the original runner

`harness/run_model.py` has the frozen trial loop unchanged. It differs from the withheld `runner.py` only
in: one adapter (OpenAI-compatible streaming), no site-specific defaults, the frozen-file check skipping
the withheld entries, a `harness` field on each public row, and the extra public results file.

## 2. Register and recompute

1. Append the public rows to `data/results.jsonl`.
2. **Append** an entry to the end of `data/models.json` (`label`, `model_ref`, `route`, `hardware_class`,
   `output_token_cap`, `latency_instrument`, optional `coverage_note`). Appending keeps every existing
   bootstrap interval unchanged, because the bootstrap draws one random stream in registry order.
3. Leave `reference/` unchanged. It holds the original run report's tables; `reproduce.py` matches the
   original models against it and lists added models as having no reference.
4. Run `python3 reproduce.py --write` (regenerates `results/` and `SHA256SUMS`), then `./reproduce.sh`
   must end in `RESULT: PASS`.

## 3. What to report

For each model: model ref and version or date, route, hardware class (for owned hardware: device, memory,
accelerator, runtime and quantisation), output and context limits, and the latency instrument. Report
power only if it was metered, and name the meter. Do not add account or usage-accounting data to rows or to
`data/models.json`.
