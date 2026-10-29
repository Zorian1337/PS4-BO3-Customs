import unittest,tempfile,json
from pathlib import Path
from report import Reporter
from capture import Collector

class ConsoleLogsTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'build');self.folder=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_session_reset_keeps_error_history(self):
  c=Collector(self.folder)
  c.session(b'[Build] test1\n[Lua] UI Error 12345: nil\nstack traceback:\ncaller.lua:22\n')
  c.reporter.flush(force=True)
  c.session(b'[Build] test2\nnormal session\n')
  self.assertEqual((self.folder/'session.log').read_bytes(),b'[Build] test2\nnormal session\n')
  self.assertIn('caller.lua:22',(self.folder/'crash-errors.log').read_text())
  self.assertEqual(c.reporter.resets,1)
 def test_full_stack_and_related_kernel(self):
  r=Reporter(self.folder);r.feed('klog','[BO3-Customs] context before the failure\n',100)
  r.feed('game','[Build] dev32\n[Transition] loaded mod 1: DS4C\n[Lua] UI Error 21544: missing main\nstack traceback:\ncaller.lua:100\n',101)
  r.flush(force=True,now=106);s=(self.folder/'crash-errors.log').read_text()
  for text in ('dev32','DS4C','caller.lua:100','related kernel context'):self.assertIn(text,s)
 def test_partial_last_error_is_saved(self):
  r=Reporter(self.folder);r.feed('game','[Lua] UI Error 9: partial');r.flush(force=True)
  self.assertIn('partial',(self.folder/'crash-errors.log').read_text())
 def test_mono_banner_is_not_a_native_crash(self):
  r=Reporter(self.folder);r.feed('klog','<118>\tSIGSEGV:       normal\n');r.flush(force=True)
  self.assertFalse((self.folder/'crash-errors.log').exists())
 def test_fatal_registers_and_module_mapping(self):
  r=Reporter(self.folder);r.feed('klog','# A user thread receives a fatal signal\n# signal: 4 (SIGILL)\n# rip: 000000000101a9a2\n# backtrace:\n# 0000000080350082\n# /data/nexHEN/plugins/BO3-Customs-dev32.sprx\n#    text: 000000008033c000:0000000080394000\n');r.flush(force=True)
  s=(self.folder/'crash-errors.log').read_text();self.assertIn('SIGILL',s);self.assertIn('8033c000',s)
 def test_rotation_and_repeat_summary(self):
  r=Reporter(self.folder,max_bytes=1200)
  for i in range(10):
   r.feed('game','[Lua] UI Error '+str(i)+': example\n',i*65);r.flush(force=True,now=i*65+5)
  self.assertTrue((self.folder/'crash-errors.log.1').exists())
  r.feed('game','[Lua] UI Error 99: repeat\n',1000);r.feed('game','[Lua] UI Error 99: repeat\n',1001);r.flush(force=True,now=1006)
  self.assertTrue(json.loads((self.folder/'status.json').read_text())['repeated'])

 def test_device_error_survives_normal_session_restart(self):
  c=Collector(self.folder);c.session(b'[Build] latest\nnormal\n')
  c.errors(b'[Build] older\n[Lua] UI Error 22: previous boot\nstack traceback:\nsaved caller\n')
  c.reporter.flush(force=True)
  self.assertIn('saved caller',(self.folder/'crash-errors.log').read_text())
  self.assertEqual((self.folder/'session.log').read_bytes(),b'[Build] latest\nnormal\n')
  before=(self.folder/'crash-errors.log').stat().st_size
  resumed=Collector(self.folder);resumed.session(b'[Build] latest\nnormal\n');resumed.errors(c.device_errors);resumed.reporter.flush(force=True)
  self.assertEqual((self.folder/'crash-errors.log').stat().st_size,before)

 def test_lobby_vm_error_is_not_lost(self):
  r=Reporter(self.folder);r.feed('game','[Lua] LobbyVM Error 74046: Attempt to call a nil value\nstack traceback:\n');r.flush(force=True)
  self.assertEqual(r.counts['lobby-vm-error'],1)
  self.assertIn('74046',(self.folder/'crash-errors.log').read_text())

if __name__=='__main__':unittest.main()
