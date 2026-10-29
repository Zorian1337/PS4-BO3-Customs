"""Error reports alongside an unchanged full session log."""
from collections import Counter,deque
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,time,os


def utc(value=None):
    return datetime.fromtimestamp(time.time() if value is None else value,timezone.utc).isoformat()


def atomic_write(path,data):
    path=Path(path);temporary=path.with_name(path.name+'.tmp')
    with temporary.open('wb') as out:
        out.write(data);out.flush();os.fsync(out.fileno())
    os.replace(temporary,path)


class Reporter:
    def __init__(self,folder,max_bytes=8*1024*1024,backups=3):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.path=self.folder/'crash-errors.log';self.maximum=max_bytes;self.backups=backups
        self.rings={'game':deque(maxlen=240),'klog':deque(maxlen=1200)}
        self.pending=[];self.recent={};self.counts=Counter();self.observations=Counter();self.latest=deque(maxlen=12);self.latest_errors=deque(maxlen=12)
        self.context={'build':'unknown','map':'unknown','selected_mods':{},'loaded_mods':{}}
        self.offline=False;self.last_status=0;self.module_name=None;self.session=1;self.sequence=0;self.resets=0;self.partial={'game':'','klog':''}
        state=self.folder/'status.json'
        if state.exists() and state.stat().st_size<1024*1024:
            try:
                previous=json.loads(state.read_text())
                self.context=previous.get('context',self.context)
                self.session=int(previous.get('session',1));self.resets=int(previous.get('resets',0))
                self.counts.update(previous.get('counts',{}));self.observations.update(previous.get('observations',{}));self.latest.extend(previous.get('latest',[])[-12:]);self.latest_errors.extend(previous.get('latest_errors',[])[-12:])
                self.sequence=max([int(v['id'][1:]) for v in self.latest]+[0])
            except (ValueError,KeyError,TypeError):pass


    def reset_game(self):
        self.flush(force=True);self.session+=1;self.resets+=1
        self.rings['game'].clear();self.recent.clear();self.partial['game']=''
        self.context={'build':'unknown','map':'unknown','selected_mods':{},'loaded_mods':{}}
        self._append('\n=== GAME LOG RESET '+utc()+'; session '+str(self.session)+' ===\n')

    def _context(self,line):
        if line.startswith('# /') and ('/app0/eboot.bin' in line or 'BO3-Customs' in line):self.module_name=line[2:]
        match=re.search(r'(?:text|xotext):\s*([0-9a-fA-F]+):([0-9a-fA-F]+)',line)
        if match and self.module_name:
            self.context.setdefault('native_modules',{})[self.module_name]=dict(base=match[1],end=match[2]);self.module_name=None
        match=re.search(r'\[Build\] (.+)',line)
        if match:self.context['build']=match[1]
        match=re.search(r'\[Transition\] (selected|loaded) mod (\d+): (.+)',line)
        if match:self.context[match[1]+'_mods'][match[2]]=match[3]
        if '[Mods] ticked: 0 mod(s)' in line:self.context['selected_mods']={}
        if re.search(r'\[Transition\].*loaded=0(?: |$)',line):self.context['loaded_mods']={}
        match=re.search(r'(?:level zones|\[Zones\] load|level=) ([a-z][a-z0-9_]+)',line)
        if match:self.context['map']=match[1]
        match=re.search(r'\[Log\] running on a (PS[45])',line)
        if match:self.context['console']=match[1]

    @staticmethod
    def category(line):
        lower=line.lower()
        if 'sigsegv:       normal' in lower or ('[asset]' not in lower and 'missing fx' in lower):return None
        if '# a user thread receives a fatal signal' in lower:return 'native-crash'
        if 'could not persist crash/error context' in lower:return 'storage-error'
        if re.search(r'LobbyVM Error \d+',line):return 'lobby-vm-error'
        if re.search(r'UI Error \d+',line):return 'ui-error'
        if '[Lua]' in line and ' failed ' in line:return 'lua-error'
        if 'out of memory' in lower or 'not enough memory' in lower or 'cannot retain' in lower or 'before loading borrowed bytecode' in lower:return 'memory-error'
        if re.search(r'(?:runtime error \d+|server script error|throwing script exception)',line,re.I):return 'script-error'
        if '[stall] the game has made no progress' in lower:return 'stall'
        if '[asset] missing ' in lower:return 'missing-asset'
        if re.search(r'\[(?:error|fatal)\]|clientfield mismatch|client mismatch|connection interrupted',line,re.I):return 'engine-error'
        return None

    @staticmethod
    def signature(category,line):
        text=re.sub(r'^.*?(?=\[\d+:\d+\.\d+\])','',line)
        text=re.sub(r'^\[\d+:\d+\.\d+\]\s*','',text)
        text=re.sub(r'(?i)runtime error \d+','runtime error',text)
        text=re.sub(r'\(occurrence \d+\)|\d+ failures','',text)
        return hashlib.sha256((category+text).encode()).hexdigest()[:20]

    def feed(self,source,text,now=None):
        now=time.time() if now is None else now
        self.rings.setdefault(source,deque(maxlen=240));self.partial.setdefault(source,'')
        text=self.partial[source]+text;rows=text.split('\n');self.partial[source]=rows.pop()
        for line in rows:
            line=line.rstrip('\r');self._context(line)
            for item in self.pending:
                if item['source']==source and len(item['after'])<100:item['after'].append(line)
            kind=self.category(line)
            self.rings[source].append((now,line))
            if not kind:continue
            if source=='klog' and '[BO3-Customs]' not in line and kind!='native-crash':continue
            self.observations[kind]+=1;key=self.signature(kind,line)
            previous=self.recent.get(key)
            if previous and now-previous['last']<60:
                previous['count']+=1;previous['last']=now;continue
            self.counts[kind]+=1;self.sequence+=1
            item=dict(id='E%06d'%self.sequence,session=self.session,source=source,category=kind,
                      trigger=line,first=now,last=now,count=1,signature=key,
                      context=json.loads(json.dumps(self.context)),before=[l for _,l in list(self.rings[source])[-26:-1]],after=[])
            self.pending.append(item);self.recent[key]=item
            if len(self.pending)>48:self._finish(self.pending.pop(0))
        self.flush(now=now)

    def flush(self,force=False,now=None):
        now=time.time() if now is None else now
        if force:
            for source in list(self.partial):
                if self.partial[source]:
                    tail=self.partial[source];self.partial[source]='';self.feed(source,tail+'\n',now)
        keep=[]
        for item in self.pending:
            if force or now-item['first']>=4:self._finish(item)
            else:keep.append(item)
        self.pending=keep
        # Persist repeat totals independently of the immutable detailed reports.
        if not force and now-self.last_status<2:return
        self.last_status=now
        state=dict(updated_utc=utc(now),session=self.session,resets=self.resets,counts=dict(self.counts),observations=dict(self.observations),
                   latest=list(self.latest),latest_errors=list(self.latest_errors),pending=len(self.pending),context=self.context,
                   repeated=[dict(signature=k,count=v['count'],last_utc=utc(v['last'])) for k,v in list(self.recent.items())[-32:] if v['count']>1])
        atomic_write(self.folder/'status.json',json.dumps(state,indent=2).encode())

    def _finish(self,item):
        related=[]
        if item['source']!='klog':
            related=[l for at,l in self.rings['klog'] if abs(at-item['first'])<15 and
                     ('[BO3-Customs]' in l or l.startswith('#') or '[Syscore App]' in l)]
        details=['\n'+'='*76, item['id']+' '+item['category'].upper(),
                 'Captured UTC: '+utc(item['first'])+'; last: '+utc(item['last']),
                 'Session: '+str(item['session'])+'; source: '+item['source']+'; repeats: '+str(item['count']),
                 'Observed context: '+json.dumps(item['context'],ensure_ascii=False),
                 'Trigger: '+item['trigger'],'--- preceding context ---',*item['before'],
                 '--- following context / stack ---',*item['after']]
        if related:details+=[('--- provided kernel context (offline; time correlation unavailable) ---' if self.offline else '--- related kernel context (capture-time correlation) ---'),*related[-100:]]
        if self.context.get('native_modules'):details+=['--- native module mapping ---',json.dumps(self.context['native_modules'])]
        details+=['--- Evidence only; the last message alone does not establish a root cause. ---','']
        self._append('\n'.join(details)+'\n')
        self.latest.append(dict(id=item['id'],category=item['category'],session=item['session'],trigger=item['trigger'][:400],captured_utc=utc(item['first'])))
        if item['category']!='missing-asset':self.latest_errors.append(self.latest[-1])

    def _append(self,text):
        encoded=text.encode('utf-8','replace')
        if self.path.exists() and self.path.stat().st_size+len(encoded)>self.maximum:
            oldest=self.folder/('crash-errors.log.'+str(self.backups))
            if oldest.exists():oldest.unlink()
            for i in range(self.backups-1,0,-1):
                p=self.folder/('crash-errors.log.'+str(i))
                if p.exists():os.replace(p,self.folder/('crash-errors.log.'+str(i+1)))
            os.replace(self.path,self.folder/'crash-errors.log.1')
        with self.path.open('ab') as out:out.write(encoded);out.flush();os.fsync(out.fileno())
