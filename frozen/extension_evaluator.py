"""Frozen R6 mutation scoring and R7 package integration scoring."""
import json,pathlib,re,subprocess,sys,time
from evaluator import execute,limits

def pytest_files(task,files,directory,targets):
 d=pathlib.Path(directory).resolve();d.mkdir(parents=True,exist_ok=False)
 for path,source in files.items():
  p=d/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)
 (d/'conftest.py').write_text('import sys\nsys.path.insert(0,'+repr(str(d))+')\n')
 cmd=[sys.executable,'-I','-m','pytest','-q','--capture=sys','-p','no:cacheprovider',*targets]
 if sys.platform=='darwin':
  # Also hide the private benchmark tree from submitted code, except its own sandbox.
  profile='(version 1)(allow default)(deny network*)(deny file-write*)(allow file-write* (literal "/dev/null"))(deny file-read-data (require-all (subpath '+json.dumps(str(pathlib.Path(__file__).resolve().parent))+') (require-not (subpath '+json.dumps(str(d))+')) (require-not (subpath '+json.dumps(sys.prefix)+'))))'
  cmd=['/usr/bin/sandbox-exec','-p',profile]+cmd
 start=time.monotonic()
 try:
  p=subprocess.run(cmd,cwd=d,capture_output=True,text=True,timeout=task['budgets']['execution_seconds'],preexec_fn=limits,env={'PATH':'/usr/bin:/bin','HOME':str(d),'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'})
  log=p.stdout+p.stderr;(d/'result.txt').write_text(log)
  passed=p.returncode==0 and bool(re.search(r'\b[1-9]\d* passed\b',log))
  killed=p.returncode==1 and bool(re.search(r'\b[1-9]\d* failed\b',log)) and 'ERROR collecting' not in log
  return dict(pass_=passed,killed=killed,returncode=p.returncode,wall_s=time.monotonic()-start,log=log[-3000:])
 except Exception as e:return dict(pass_=False,killed=False,error=type(e).__name__+': '+str(e))

def score(task,answers,calls,directory,trap=False):
 if trap:return {'pass':answers[-1].strip()==task['trap']['expected'],'kind':'abstention'}
 d=pathlib.Path(directory)
 try:
  files=json.loads(answers[-1])['files']
  if not isinstance(files,dict) or any(not isinstance(v,str) for v in files.values()):raise ValueError('invalid files mapping')
  if task['rung']==6:
   if set(files)!={'solution.py','test_solution.py'}:raise ValueError('requires exactly solution.py and test_solution.py')
   contract='import pytest\nfrom solution import *\ndef test_contract():\n'+''.join(' '+s+'\n' for s in task['tests'].splitlines())
   code=pytest_files(task,{'solution.py':files['solution.py'],'test_contract.py':contract},d/'behavior',['test_contract.py'])
   ref=pytest_files(task,{'solution.py':task['reference'],'test_solution.py':files['test_solution.py']},d/'reference',['test_solution.py'])
   mutants=[pytest_files(task,{'solution.py':m,'test_solution.py':files['test_solution.py']},d/f'mutant-{i}',['test_solution.py']) for i,m in enumerate(task['mutants'],1)]
   kills=sum(x['killed'] for x in mutants);rate=kills/len(mutants)
   return {'pass':code['pass_'] and ref['pass_'] and rate>=.8,'behavior':code,'tests_on_reference':ref,'mutants':mutants,'mutants_killed':kills,'mutants_total':len(mutants),'mutation_kill_rate':rate}
  allowed=set(task['required_paths'])|{'pkg/__init__.py'}
  if set(files)-allowed:raise ValueError('patch outside source allowlist')
  changed=[p for p in files if files[p]!=task['files'][p]]
  if len(changed)<3 or not set(task['required_paths']).issubset(changed):raise ValueError('must change all three feature source files')
  merged={**task['files'],**files}
  merged['test_feature.py']='from pkg import *\ndef test_feature():\n'+''.join(' '+s+'\n' for s in task['tests'].splitlines())
  old=pytest_files(task,merged,d/'existing',['test_existing.py'])
  new=pytest_files(task,merged,d/'feature',['test_feature.py'])
  return {'pass':old['pass_'] and new['pass_'],'existing':old,'feature':new,'changed_paths':changed}
 except Exception as e:return {'pass':False,'error':type(e).__name__+': '+str(e)}
