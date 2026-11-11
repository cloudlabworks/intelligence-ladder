---
title: Intelligence Ladder Leaderboard
emoji: 🪜
colorFrom: indigo
colorTo: gray
sdk: gradio
sdk_version: 6.31.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: Frozen coding ladder, hosted vs edge NPU models
---

# Intelligence Ladder Leaderboard

Read-only leaderboard for the Intelligence Ladder benchmark. The app reads only `data/results.jsonl` and
`data/models.json` shipped in this Space and builds every table with `ladder.py`, the same code the
`reproduce.py` check uses. No inference, no uploads, no network calls.

Space contents: `app.py`, `ladder.py`, `requirements.txt`, `data/results.jsonl`, `data/models.json`,
and this file as `README.md`.

Data: CC BY 4.0. Code: MIT.
