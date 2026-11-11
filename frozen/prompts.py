import json
SYSTEM='You are taking a frozen programming benchmark. Follow only the task. Do not use external tools or inspect local files. The only tools are the simulated read interface explicitly supplied in R4. Do not explain your answer.'
def initial(task,trap=False):
 if trap:return task['trap']['prompt']
 p=task['prompt']
 if task['rung']==4:
  return p+'\nTools (OpenClaw read schema restricted to path/offset/limit): '+json.dumps(task['tools'])+'\nMax calls: 2. Request reads as exactly {"tool_calls":[{"name":"read","arguments":{"path":"worker.py"}},{"name":"read","arguments":{"path":"config.py"}}]}. The harness dispatches these against canned file contents. After receiving outputs, return a JSON object with files (path->full replacement source) and tool_calls (the exact ordered calls actually made). No Markdown.'
 if 'files' in task:
  return p+'\nFiles:\n'+json.dumps(task['files'])+'\nReturn exactly one JSON object {"files":{"path":"full replacement source"}} containing only modified files. No Markdown.'
 return p+'\nReturn only Python source, no Markdown or explanation.'
def changed(task):return task['turn2']+'\nReturn the complete final Python source, not a diff. No Markdown or explanation.'
def tool_reply(task,calls):
 if not isinstance(calls,list):raise ValueError('tool_calls must be list')
 out=[]
 for call in calls:
  if call not in task['expected_calls']:raise ValueError('unexpected tool or arguments')
  out.append({'call':call,'output':task['files'][call['arguments']['path']]})
 return 'Canned tool results: '+json.dumps(out)+'\nNow return the patch as files plus the exact tool_calls made, as a single JSON object.'
