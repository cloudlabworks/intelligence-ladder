#!/usr/bin/env python3
"""Run a model on the frozen ladder through any OpenAI-compatible streaming endpoint.

Public runner. The trial loop is the frozen runner's loop unchanged; the differences are listed in
CONTRIBUTING.md (OpenAI-compatible adapter only, no site-specific defaults, a public results file
with execution logs removed). It imports the frozen prompts and evaluators from ../frozen and
refuses to run if any shipped frozen file differs from frozen/SHA256SUMS.json.

  python3 harness/run_model.py --model ORG/MODEL --label my-model \
      --base-url http://127.0.0.1:8000/v1 --out runs/my-model

The API key, if any, is read from the environment variable named by --key-env.

SECURITY: the evaluator executes model-written code. On macOS it uses sandbox-exec (no network,
no file writes outside the trial directory). On Linux it only applies rlimits: run inside a
disposable container or VM.
"""
import argparse
import hashlib
import json
import os
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FROZEN = ROOT / 'frozen'
sys.path.insert(0, str(FROZEN))

from evaluator import score, object_text  # noqa: E402
from extension_evaluator import score as extension_score  # noqa: E402
from prompts import SYSTEM, initial, changed, tool_reply  # noqa: E402

WITHHELD_PREFIXES = ('hidden/', 'runner.py')
HARNESS = 'public-run_model-v1'


def verify():
    manifest = json.loads((FROZEN / 'SHA256SUMS.json').read_text())
    for p, h in manifest.items():
        if p.startswith(WITHHELD_PREFIXES):
            continue
        assert hashlib.sha256((FROZEN / p).read_bytes()).hexdigest() == h, 'Frozen file changed: ' + p
    return hashlib.sha256((FROZEN / 'SHA256SUMS.json').read_bytes()).hexdigest()


class OpenAICompatible:
    def __init__(self, model, url, key_env='LADDER_API_KEY'):
        self.model = model
        self.url = url.rstrip('/') + '/chat/completions'
        self.key_env = key_env

    def generate(self, messages, budget, d):
        payload = dict(model=self.model, messages=messages, temperature=0, max_tokens=budget['max_output_tokens'],
                       stream=True, stream_options={'include_usage': True})
        headers = {'Content-Type': 'application/json'}
        if os.environ.get(self.key_env):
            headers['Authorization'] = 'Bearer ' + os.environ[self.key_env]
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers)
        start = time.monotonic()
        first = last = None
        parts, usage, events = [], {}, []
        context = ssl.create_default_context(cafile=os.environ['SSL_CERT_FILE']) if os.environ.get('SSL_CERT_FILE') else None
        # 429 = rejected before inference: back off and resend; a scored answer is never retried.
        for attempt in range(6):
            try:
                response = urllib.request.urlopen(req, timeout=budget['model_turn_seconds'], context=context)
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 5:
                    raise
                time.sleep(min(120, int(e.headers.get('Retry-After') or 0) or 10 * 2 ** attempt))
        with response:
            for raw in response:
                if time.monotonic() - start > budget['model_turn_seconds']:
                    raise TimeoutError('stream deadline')
                line = raw.decode().strip()
                if not line.startswith('data:'):
                    continue
                data = line[5:].strip()
                if data == '[DONE]':
                    break
                event = json.loads(data)
                events.append(event)
                if event.get('error'):
                    raise RuntimeError('SSE provider error: ' + json.dumps(event['error'])[:1000])
                if event.get('usage'):
                    usage = event['usage']
                for choice in event.get('choices', []):
                    chunk = choice.get('delta', {}).get('content')
                    if chunk:
                        now = time.monotonic()
                        first = first or now
                        last = now
                        parts.append(chunk)
        wall = time.monotonic() - start
        tokens = usage.get('completion_tokens')
        (d / 'events.json').write_text(json.dumps(events, indent=2))
        return dict(text=''.join(parts), wall_s=wall, ttft_s=first - start if first else None,
                    tok_s=(tokens - 1) / (last - first) if tokens and first and last > first else None,
                    output_tokens=tokens, usage=usage,
                    metric_source='SSE first content event; (completion_tokens-1)/first-to-last content elapsed, if usage supplied')


def trial(adapter, task, repeat, trap, out, model, freeze):
    """Unchanged from the frozen runner."""
    id = f"{task['id']}-{'trap' if trap else 'code'}-{repeat}"
    d = out / 'runs' / id
    d.mkdir(parents=True, exist_ok=False)
    messages = [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': task['prompt'] if task['rung'] == 6 and not trap else initial(task, trap)}]
    answers, calls, metrics = [], [], []
    start = time.monotonic()
    row = dict(id=id, task=task['id'], rung=task['rung'], repeat=repeat, trap=trap, model=model, freeze_sha256=freeze)
    try:
        count = 1 if trap else task['budgets']['max_model_turns']
        for turn in range(count):
            td = d / f'turn-{turn + 1}'
            td.mkdir()
            (td / 'messages.json').write_text(json.dumps(messages, ensure_ascii=False, indent=2) + '\n')
            if time.monotonic() - start > task['budgets']['task_seconds']:
                raise TimeoutError('task deadline')
            result = adapter.generate(messages, task['budgets'], td)
            text = result.pop('text')
            metrics.append(result)
            (td / 'answer.txt').write_text(text)
            messages.append({'role': 'assistant', 'content': text})
            if not trap and task['rung'] == 4:
                try:
                    obj = object_text(text)
                except Exception:
                    answers.append(text)
                    break
                if 'files' in obj:
                    answers.append(text)
                    break
                requested = obj.get('tool_calls', [])
                if not requested or len(calls) + len(requested) > task['budgets']['max_tool_calls']:
                    raise ValueError('tool budget exceeded or no tool call')
                reply = tool_reply(task, requested)
                calls.extend(requested)
                (td / 'tool-results.json').write_text(json.dumps({'calls': requested, 'reply': reply}, indent=2))
                messages.append({'role': 'user', 'content': reply})
            else:
                answers.append(text)
                if not trap and task['rung'] == 5 and turn == 0:
                    messages.append({'role': 'user', 'content': changed(task)})
                else:
                    break
        row['score'] = (extension_score if task['rung'] >= 6 else score)(task, answers, calls, d / 'execution', trap) \
            if answers else {'pass': False, 'error': 'No final answer within turn budget'}
    except ValueError as e:
        row['score'] = {'pass': False, 'error': str(e)}
    except Exception as e:
        row['score'] = {'pass': False, 'error': type(e).__name__ + ': ' + str(e)}
        row['infrastructure_error'] = True
    row.update(wall_s=time.monotonic() - start, turn_metrics=metrics)
    (d / 'measurement.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


# ------------------------------------------------------------------ public row (same rules as data/results.jsonl)
def _sub(x):
    return {k: x[k] for k in ('pass', 'pass_', 'killed', 'returncode') if k in x}


def public_row(r):
    s = {}
    for k, v in r['score'].items():
        if k in ('wall_s', 'log', 'error'):
            if k == 'error' and 'returncode' not in r['score'] and isinstance(v, str) and '/' not in v:
                s['error'] = v[:200]
            continue
        if isinstance(v, dict) and k != 'actual_calls':
            s[k] = _sub(v)
        elif k == 'mutants':
            s[k] = [_sub(m) for m in v]
        else:
            s[k] = v
    turns = []
    for t in r['turn_metrics']:
        o = {k: t[k] for k in ('wall_s', 'ttft_s', 'inference_s', 'tok_s', 'output_tokens', 'metric_source') if k in t}
        u = t.get('usage') or {}
        if u:
            o['usage'] = {k: u[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens') if k in u}
            rt = (u.get('completion_tokens_details') or {}).get('reasoning_tokens')
            if rt is not None:
                o['usage']['reasoning_tokens'] = rt
        turns.append(o)
    out = {k: r[k] for k in ('id', 'task', 'rung', 'repeat', 'trap', 'model', 'freeze_sha256')}
    out.update(score=s, wall_s=r['wall_s'], turn_metrics=turns, harness=HARNESS)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True, help='model id sent to the endpoint')
    p.add_argument('--label', help='result label (default: --model)')
    p.add_argument('--base-url', required=True, help='OpenAI-compatible base URL ending in /v1')
    p.add_argument('--key-env', default='LADDER_API_KEY', help='name of the env var holding the API key')
    p.add_argument('--out', required=True)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--tasks', nargs='*', help='task ids, e.g. R1-A R1-B (default: all 28)')
    a = p.parse_args()
    freeze = verify()
    out = pathlib.Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    resultfile = out / 'results.jsonl'
    if resultfile.exists() and not a.resume:
        raise RuntimeError('Results already exist; use --resume')
    previous = [json.loads(l) for l in resultfile.read_text().splitlines()] if resultfile.exists() else []
    assert all(r['freeze_sha256'] == freeze for r in previous), 'Cannot mix frozen suites'
    done = {r['id'] for r in previous}
    adapter = OpenAICompatible(a.model, a.base_url, a.key_env)
    for path in sorted((FROZEN / 'rungs').glob('R*.json')):
        for task in json.loads(path.read_text()):
            if a.tasks and task['id'] not in a.tasks:
                continue
            for trap in [False, True]:
                for repeat in range(1, 4):
                    id = f"{task['id']}-{'trap' if trap else 'code'}-{repeat}"
                    if id in done:
                        continue
                    row = trial(adapter, task, repeat, trap, out, a.label or a.model, freeze)
                    with resultfile.open('a') as f:
                        f.write(json.dumps(row) + '\n')
                    with (out / 'results.public.jsonl').open('a') as f:
                        f.write(json.dumps(public_row(row)) + '\n')
                    print(id, row['score']['pass'], round(row['wall_s'], 2), flush=True)
                    # Model-answer failures never stop a run; infrastructure failures do.
                    if row.get('infrastructure_error'):
                        (out / 'BLOCKED.json').write_text(json.dumps(row, indent=2))
                        raise SystemExit(2)
    (out / 'DONE').write_text('All selected tasks, three productive and three trap repeats each.\n')


if __name__ == '__main__':
    main()
