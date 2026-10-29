"""Small CLI for persistent console error collection and compact offline review."""
import argparse,json,os
from pathlib import Path
from capture import capture
from report import Reporter

DEFAULT=Path(__file__).resolve().parents[3]/'reports'/'console-diagnostics'
ROOT=Path(__file__).resolve().parents[2]
LOCAL=ROOT/'.local/console.json'
settings=json.loads(LOCAL.read_text()) if LOCAL.exists() else {}
parser=argparse.ArgumentParser(description=__doc__)
sub=parser.add_subparsers(dest='command',required=True)
p=sub.add_parser('capture');p.add_argument('--host',default=os.environ.get('BO3_CONSOLE_HOST') or settings.get('host'));p.add_argument('--ftp-port',type=int,default=2121);p.add_argument('--klog-port',type=int,default=3232)
p.add_argument('--minutes',type=float,default=5);p.add_argument('--until-stopped',action='store_true');p.add_argument('--once',action='store_true');p.add_argument('--no-klog',action='store_true');p.add_argument('--poll',type=float,default=2);p.add_argument('--output',type=Path,default=DEFAULT)
p=sub.add_parser('summary');p.add_argument('--output',type=Path,default=DEFAULT);p.add_argument('--details',action='store_true')
p=sub.add_parser('incident');p.add_argument('id');p.add_argument('--output',type=Path,default=DEFAULT);p.add_argument('--max-lines',type=int,default=140)
p=sub.add_parser('symbolize');p.add_argument('--elf',type=Path,required=True);p.add_argument('--base',type=lambda v:int(v,0),required=True);p.add_argument('addresses',nargs='+',type=lambda v:int(v,0))
p=sub.add_parser('analyze');p.add_argument('session',type=Path);p.add_argument('--klog',type=Path);p.add_argument('--output',type=Path,default=DEFAULT)
if __name__=='__main__':
 args=parser.parse_args()
 if args.command=='capture':
  if not args.host:parser.error('Set --host, BO3_CONSOLE_HOST or ignored .local/console.json')
  if args.poll<1 or args.minutes<=0:parser.error('poll must be at least1 second and minutes positive')
  capture(args)
 elif args.command=='summary':
  p=args.output/'status.json'
  if not p.exists():print('No saved capture status yet.')
  else:
   state=json.loads(p.read_text())
   if args.details:print(json.dumps(state,indent=2))
   else:print(json.dumps(dict(session=state['session'],resets=state['resets'],counts=state['counts'],build=state['context'].get('build'),map=state['context'].get('map'),latest=[dict(id=i['id'],category=i['category'],trigger=i['trigger'][:200]) for i in (state.get('latest_errors') or state['latest'])[-5:]]),indent=2))
 elif args.command=='incident':
  found=False
  for path in [args.output/'crash-errors.log']+sorted(args.output.glob('crash-errors.log.*')):
   if not path.is_file():continue
   text=path.read_text(errors='replace');start=text.find('\n'+args.id+' ')
   if start>=0:
    end=text.find('\n'+'='*76,start);part=text[start:end if end>=0 else None]
    print('\n'.join(part.splitlines()[:args.max_lines]));found=True;break
  if not found:print('Incident not found in retained logs.')
 elif args.command=='symbolize':
  import os,shutil,subprocess
  if not args.elf.is_file():parser.error('local matching ELF does not exist')
  offsets=[hex(v-args.base) for v in args.addresses]
  if any(v<args.base for v in args.addresses):parser.error('address precedes module base')
  if os.name=='nt':
   path=args.elf.resolve();linux='/mnt/'+path.drive[0].lower()+path.as_posix()[2:]
   command=['wsl.exe','-d','Debian','--exec','llvm-addr2line-18','-f','-C','-e',linux,*offsets]
  else:command=[shutil.which('llvm-addr2line-18') or 'llvm-addr2line','-f','-C','-e',str(args.elf),*offsets]
  subprocess.run(command,check=True,timeout=20)
 else:
  report=Reporter(args.output);report.offline=True
  if args.klog:report.feed('klog',args.klog.read_text(errors='replace'))
  report.feed('game',args.session.read_text(errors='replace'));report.flush(force=True)
  print(str(args.output/'crash-errors.log'))
