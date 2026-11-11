#!/usr/bin/env python3
"""Offline smoke tests. No network beyond 127.0.0.1, no server left running.

1. Space logic: import app, build every table from the shipped data.
2. Space UI: construct the Gradio Blocks without launching (skipped if gradio is not installed).
3. Harness: run harness/run_model.py against a local mock OpenAI-compatible SSE server that returns the
   reference solutions, and check the frozen evaluators score them as passes and traps as abstentions.
   Needs pytest in the interpreter that runs this file.
"""
import http.server
import json
import pathlib
import subprocess
import sys
import tempfile
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
import ladder  # noqa: E402


def check_tables():
    t = app.build_tables()
    headers, rows = t['leaderboard']
    assert len(rows) == 8 and len(headers) == len(rows[0]), (len(rows), len(headers))
    assert [r[1] for r in rows][:1] == ['astra'], rows[0]
    print(f"tables ok: leaderboard {len(rows)} models x {len(headers)} columns, capability {len(t['capability'][1])} rows, "
          f"trials {t['trials']}")


def check_ui():
    try:
        import gradio
    except ImportError:
        print('ui skipped: gradio not installed')
        return
    demo = app.build_ui()
    assert type(demo).__name__ == 'Blocks'
    print(f'ui ok: gradio {gradio.__version__} Blocks built, not launched')


def mock_answers():
    refs = json.loads((ROOT / 'frozen' / 'references.json').read_text())
    ext = json.loads((ROOT / 'frozen' / 'extension_references.json').read_text())
    tasks = {t['id']: t for p in sorted((ROOT / 'frozen' / 'rungs').glob('R*.json')) for t in json.loads(p.read_text())}
    answers = {}
    answers[tasks['R1-A']['prompt']] = refs['R1-A']
    answers[tasks['R6-A']['prompt']] = json.dumps({'files': ext['R6-A']['files']})
    for tid in ('R1-A', 'R6-A'):
        answers[tasks[tid]['trap']['prompt']] = tasks[tid]['trap']['expected']
    return answers


class Mock(http.server.BaseHTTPRequestHandler):
    answers = {}

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        user = body['messages'][-1]['content']
        text = next((v for k, v in self.answers.items() if user.startswith(k)), 'no match')
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        half = len(text) // 2
        for chunk in (text[:half], text[half:]):
            ev = {'choices': [{'delta': {'content': chunk}}]}
            self.wfile.write(b'data: ' + json.dumps(ev).encode() + b'\n\n')
        usage = {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}
        self.wfile.write(b'data: ' + json.dumps({'choices': [], 'usage': usage}).encode() + b'\n\n')
        self.wfile.write(b'data: [DONE]\n\n')


def check_harness():
    Mock.answers = mock_answers()
    srv = http.server.HTTPServer(('127.0.0.1', 0), Mock)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'run'
            p = subprocess.run([sys.executable, str(ROOT / 'harness' / 'run_model.py'), '--model', 'mock/reference',
                                '--label', 'mock-reference', '--base-url', f'http://127.0.0.1:{srv.server_port}/v1',
                                '--out', str(out), '--tasks', 'R1-A', 'R6-A'], capture_output=True, text=True, timeout=300)
            assert p.returncode == 0, p.stdout + p.stderr
            rows = [json.loads(l) for l in (out / 'results.public.jsonl').read_text().splitlines()]
            assert len(rows) == 12 and all(r['score']['pass'] for r in rows), \
                [(r['id'], r['score']) for r in rows if not r['score']['pass']]
            raw = (out / 'results.public.jsonl').read_text()
            assert tmp not in raw and '/Users/' not in raw and '/home/' not in raw, 'local path leaked into public rows'
            r6 = [r for r in rows if r['task'] == 'R6-A' and not r['trap']]
            assert all(r['score']['mutants_killed'] == 5 for r in r6)
            board = {s['model']: s for s in ladder.leaderboard(rows, {'models': []})}
            assert board['mock-reference']['solved'] == 2
            print(f'harness ok: {len(rows)}/12 mock trials pass (R1-A, R6-A reference answers; traps abstain); '
                  f'public rows carry no local paths')
            # Negative control: R1-B has no mock answer, so every productive and trap trial must fail.
            neg = pathlib.Path(tmp) / 'neg'
            p = subprocess.run([sys.executable, str(ROOT / 'harness' / 'run_model.py'), '--model', 'mock/wrong',
                                '--base-url', f'http://127.0.0.1:{srv.server_port}/v1', '--out', str(neg),
                                '--tasks', 'R1-B'], capture_output=True, text=True, timeout=300)
            assert p.returncode == 0, p.stdout + p.stderr
            rows = [json.loads(l) for l in (neg / 'results.public.jsonl').read_text().splitlines()]
            assert len(rows) == 6 and not any(r['score']['pass'] for r in rows)
            print('harness negative control ok: 0/6 wrong-answer trials pass')
    finally:
        srv.shutdown()


if __name__ == '__main__':
    check_tables()
    check_ui()
    check_harness()
    print('SMOKE: PASS')
