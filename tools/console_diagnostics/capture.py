"""Read-only console collection. Never uploads or reads plugin binaries."""
from ftplib import FTP
from pathlib import Path
from collections import deque
import codecs,json,queue,socket,threading,time
from report import Reporter,atomic_write,utc

SESSION='/data/BO3-Customs/log.txt'
ERRORS='/data/BO3-Customs/crash-errors.log'
MAX_REMOTE=16*1024*1024


def fetch(host,port,path,timeout=5):
    ftp=FTP();ftp.connect(host,port,timeout=timeout)
    try:
        ftp.login();data=bytearray()
        def receive(block):
            if len(data)+len(block)>MAX_REMOTE:raise ValueError('remote log exceeds16MiB; original console file unchanged')
            data.extend(block)
        ftp.retrbinary('RETR '+path,receive)
        return bytes(data)
    finally:
        try:ftp.close()
        except OSError:pass


class Collector:
    def __init__(self,folder):
        self.folder=Path(folder);self.reporter=Reporter(self.folder);self.previous=None
        self.device_errors=None
        for name,attribute in (('session.log','previous'),('device-crash-errors.log','device_errors')):
            path=self.folder/name
            if path.exists() and path.stat().st_size<=MAX_REMOTE:setattr(self,attribute,path.read_bytes())
        self.kernel_decoder=codecs.getincrementaldecoder('utf-8')('replace')

    def session(self,data):
        old=self.previous
        if data==old:return
        reset=old is not None and not data.startswith(old)
        if reset:self.reporter.reset_game()
        delta=data[len(old):] if old is not None and not reset else data
        # Only the latest session mirror is replaced; crash-errors.log persists.
        atomic_write(self.folder/'session.log',data)
        self.reporter.feed('game',delta.decode('utf-8','replace'))
        self.previous=data

    def errors(self,data):
        if data!=self.device_errors:
            old=self.device_errors
            delta=data[len(old):] if old is not None and data.startswith(old) else data
            if old is not None and not data.startswith(old):atomic_write(self.folder/'device-crash-errors.log.1',old)
            atomic_write(self.folder/'device-crash-errors.log',data)
            self.reporter.feed('device-error',delta.decode('utf-8','replace'))
            self.device_errors=data

    def kernel(self,data):
        self.reporter.feed('klog',self.kernel_decoder.decode(data))


def kernel_reader(host,port,out,stop):
    while not stop.is_set():
        try:
            with socket.create_connection((host,port),timeout=4) as sock:
                sock.settimeout(1)
                while not stop.is_set():
                    try:data=sock.recv(65536)
                    except socket.timeout:continue
                    if not data:break
                    # Bound transient memory; preserve the newest failure burst.
                    try:out.put(('klog',data),timeout=1)
                    except queue.Full:
                        try:out.get_nowait()
                        except queue.Empty:pass
                        try:out.put_nowait(('gap',b'Kernel collector backlog; one block omitted.\n'))
                        except queue.Full:pass
        except OSError as exc:
            try:out.put_nowait(('notice',('klog reconnect: '+str(exc)).encode()))
            except queue.Full:pass
        stop.wait(2)


def capture(args):
    folder=Path(args.output);folder.mkdir(parents=True,exist_ok=True)
    collector=Collector(folder);stop=threading.Event();events=queue.Queue(maxsize=64)
    thread=threading.Thread(target=kernel_reader,args=(args.host,args.klog_port,events,stop),daemon=True)
    if not args.no_klog:thread.start()
    end=time.monotonic()+args.minutes*60 if not args.until_stopped else float('inf')
    next_ftp=0;next_status=0;last_issue=None;first=True
    print('Read-only capture: '+str(folder),flush=True)
    try:
        while time.monotonic()<end:
            now=time.monotonic()
            if now>=next_ftp:
                try:
                    collector.session(fetch(args.host,args.ftp_port,SESSION))
                except Exception as exc:
                    issue=type(exc).__name__+': '+str(exc)
                    if issue!=last_issue:print('Retrying: '+issue,flush=True);last_issue=issue
                # A missing/oversized session must not prevent reading persistent errors.
                try:collector.errors(fetch(args.host,args.ftp_port,ERRORS))
                except Exception:pass # Older plugins do not have the persistent error log.
                if args.once:break
                next_ftp=now+args.poll
            try:
                source,data=events.get(timeout=.2)
                if source=='klog':collector.kernel(data)
                elif source=='gap':collector.reporter._append('[Collector] '+data.decode())
            except queue.Empty:pass
            collector.reporter.flush()
            if now>=next_status:
                print('Saved errors: '+json.dumps(dict(collector.reporter.counts))+'; session '+str(collector.reporter.session),flush=True)
                next_status=now+30
    except KeyboardInterrupt:pass
    finally:
        stop.set()
        if thread.is_alive():thread.join(timeout=5)
        while not events.empty():
            source,data=events.get_nowait()
            if source=='klog':collector.kernel(data)
        collector.reporter.flush(force=True)
        print('Saved: '+str(folder/'crash-errors.log')+' (full session mirror remains session.log)',flush=True)
