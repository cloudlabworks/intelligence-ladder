"""Frozen behavioural evaluator; no LLM judges or text similarity."""
import json,os,pathlib,re,resource,subprocess,sys,time

def code_text(text):
 text=text.strip()
 m=re.fullmatch(r'```(?:python)?\s*\n(.*?)\n```',text,re.S)
 return m.group(1) if m else text

def object_text(text):
 # JSON is intentionally whole-document strict, no prose or Markdown stripping.
 return json.loads(text)

def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(6,6))
 resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
 resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
 if sys.platform!='darwin':resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))

def execute(task,answer,assertions,directory):
 d=pathlib.Path(directory).resolve();d.mkdir(parents=True,exist_ok=True)
 try:
  files=dict(task.get('files',{}))
  if files:
   obj=object_text(answer)
   patch=obj.get('files')
   if not isinstance(patch,dict) or not patch: raise ValueError('files must be a nonempty path->full replacement source mapping')
   allowed={'worker.py'} if task['rung']==4 else set(files)
   if set(patch)-allowed:raise ValueError('patch path outside frozen allowlist')
   if any(not isinstance(v,str) for v in patch.values()):raise ValueError('source must be string')
   files.update(patch); entry=task['entry']
  else:files={'solution.py':code_text(answer)};entry='solution'
  for path,source in files.items():
   p=d/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)
  test='import sys\nsys.path.insert(0,'+repr(str(d))+')\nfrom '+entry+' import *\n\ndef test_contract():\n'+''.join('    '+s+'\n' for s in assertions.splitlines())
  (d/'test_contract.py').write_text(test)
  cmd=[sys.executable,'-I','-m','pytest','-q','--capture=sys','-p','no:cacheprovider',str(d/'test_contract.py')]
  if sys.platform=='darwin':
   profile='(version 1)(allow default)(deny network*)(deny file-write*)(allow file-write* (literal "/dev/null"))'
   cmd=['/usr/bin/sandbox-exec','-p',profile]+cmd
  start=time.monotonic()
  p=subprocess.run(cmd,cwd=d,capture_output=True,text=True,timeout=task['budgets']['execution_seconds'],preexec_fn=limits,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','HOME':str(d)})
  log=p.stdout+p.stderr;(d/'result.txt').write_text(log)
  return {'pass':p.returncode==0 and bool(re.search(r'\b1 passed\b',log)),'returncode':p.returncode,'wall_s':time.monotonic()-start,'error':log[-2500:] if p.returncode else None}
 except Exception as e:return {'pass':False,'error':type(e).__name__+': '+str(e)}

def score(task,answers,calls,directory,trap=False):
 if trap:return {'pass':answers[-1].strip()==task['trap']['expected'],'kind':'abstention'}
 d=pathlib.Path(directory)
 if task['rung']==5:
  if len(answers)!=2:return {'pass':False,'error':'requires both turns'}
  initial=execute(task,answers[0],task['tests'],d/'turn1')
  final=execute(task,answers[1],task['final_tests'],d/'turn2')
  obsolete=execute(task,answers[1],task['conflict_tests'],d/'obsolete')
  rejected_old=obsolete.get('returncode')==1 and 'AssertionError' in (obsolete.get('error') or '')
  return {'pass':initial['pass'] and final['pass'] and rejected_old,'initial':initial,'final':final,'obsolete_rejected':rejected_old}
 result=execute(task,answers[-1],task['tests'],d/'final')
 if task['rung']==4:
  try:claimed=object_text(answers[-1]).get('tool_calls')
  except Exception:claimed=None
  exact=calls==task['expected_calls'] and claimed==calls
  result={'pass':result['pass'] and exact,'code':result,'tool_exact':exact,'actual_calls':calls}
 return result
