"""Compact SPRX/Lua handoff and source-publication guard. No model/API calls."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
BLOCKED_SUFFIXES={'.sprx','.elf','.oelf','.bin','.exe','.dll','.zip','.7z','.ff','.xpak','.luac','.pyc','.dmp'}
ALLOWED_ROOTS={'.github','SPRX','Lua','docs'}
ALLOWED_FILES={'.gitignore','AGENTS.md','RESUME.md','README.md','LICENSE','CHANGELOG.md','WATCH_CONSOLE.cmd','RESUME_WORK.cmd','CHECK_SOURCE.cmd','tools/project_session.py','tools/test_project_session.py'}


def git(*args):
 return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf-8',errors='replace').rstrip()


def path_issue(name):
 p=PurePosixPath(name);lower=name.lower();parts={v.lower() for v in p.parts}
 if p.is_absolute() or '..' in parts:return 'unsafe source path'
 if parts & {'build','reports','research','private','.local','__pycache__','releases'}:return 'local/private/generated directory'
 if p.suffix.lower() in BLOCKED_SUFFIXES:return 'binary/content artifact belongs outside source commits'
 if 'daybreak' in lower or 'eboot' in p.name.lower():return 'private/reconstruction artifact name'
 if p.name.startswith('.env') or p.name=='console.local.json':return 'local configuration or secret file'
 if name not in ALLOWED_FILES and p.parts[0] not in ALLOWED_ROOTS and not name.startswith('tools/console_diagnostics/'):return 'outside the SPRX/Lua maintenance scope'
 return None


def text_issue(data):
 if b'\0' in data:return 'binary bytes in a source file'
 try:text=data.decode('utf-8-sig')
 except UnicodeError:return 'non-UTF8 source; review before publication'
 patterns=[(r'discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+','webhook credential'),
           (r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}','GitHub credential'),
           (r'(?i)[A-Z]:[/\\]Users[/\\][^\s<>]+','personal user path'),
           (r'192\.168\.68\.\d+','personal console address'),
           (r'(?i)' + 'zm' + '8p|' + 'BO3-18-' + 'Player-Zombies','private gameplay project reference')]
 for pattern,label in patterns:
  if re.search(pattern,text):return label
 return None


def audit(commit=None):
 command=['diff-tree','--root','--no-commit-id','--name-status','-r',commit] if commit else ['diff','--cached','--name-status','--no-renames']
 rows=git(*command).splitlines();errors=[];checked=0
 for row in rows:
  status,*names=row.split('\t');name=names[-1]
  if status.startswith('D'):continue
  issue=path_issue(name)
  if not issue:
   ref=(commit+':'+name) if commit else ':'+name
   data=subprocess.check_output(['git','show',ref],cwd=ROOT)
   issue=text_issue(data)
  if issue:errors.append(dict(path=name,reason=issue))
  checked+=1
 print(json.dumps(dict(checked=checked,failures=errors,scope='changed source only; existing upstream data is not silently removed'),indent=2))
 return bool(errors)


def status():
 source=(ROOT/'SPRX/main.cpp').read_text(encoding='utf-8')
 match=re.search(r'\[Build\] ([^"\n]+)',source)
 rows=git('status','--porcelain').splitlines()
 state=dict(repository='Zorian1337/PS4-BO3-Customs',branch=git('branch','--show-current'),head=git('rev-parse','--short','HEAD'),source_label=match[1] if match else 'unknown',release_ready=False,dirty_count=len(rows),changed_paths=[v[3:] for v in rows[:30]],resume='RESUME.md',next='GPU/native stall investigation and unbuilt readiness guard; see docs/DEVELOPMENT.md')
 for name in ('origin/main','upstream/main'):
  try:state[name]=git('rev-parse','--short',name)
  except subprocess.CalledProcessError:state[name]='not fetched'
 print(json.dumps(state,indent=2));return 0


def test():
 path=ROOT/'.local/session.json'
 if path.exists():
  settings=json.loads(path.read_text());command=settings.get('test_command')
  if isinstance(command,list) and command and all(isinstance(v,str) for v in command):
   return subprocess.run(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')).returncode
 return subprocess.run([sys.executable,'.github/scripts/run_host_checks.py'],cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')).returncode


def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
 sub.add_parser('status');p=sub.add_parser('audit');p.add_argument('--commit');sub.add_parser('test')
 args=parser.parse_args()
 return status() if args.action=='status' else audit(args.commit) if args.action=='audit' else test()

if __name__=='__main__':raise SystemExit(main())
