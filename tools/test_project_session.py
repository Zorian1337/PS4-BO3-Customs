"""Publication policy: reject private artifacts without printing their contents."""
import unittest
from project_session import path_issue,text_issue
class PublicationChecks(unittest.TestCase):
 def test_source_allowed(self):
  for name in ('SPRX/t7_lua.cpp','Lua/ui_scripts/mods.lua','docs/DEVELOPMENT.md','tools/console_diagnostics/report.py','RESUME.md'):self.assertIsNone(path_issue(name))
 def test_artifacts_rejected(self):
  for name in ('Releases/plugin.sprx','build/native.elf','reports/log.txt','private/notes.md','research/reconstruction.md','.local/session.json','Lua/menu.luac','SPRX/payload.bin','../file.cpp','Tool/unrelated.cs'):self.assertIsNotNone(path_issue(name),name)
 def test_secrets_and_personal_paths(self):
  samples=['discord.com/api/'+'webhooks/123456/'+'token_is_private','ghp_'+'x'*30,chr(67)+':'+chr(92)+'Users'+chr(92)+'example'+chr(92)+'notes']
  for text in samples:self.assertIsNotNone(text_issue(text.encode()))
 def test_normal_source(self):self.assertIsNone(text_issue(b'void Test() {}\n'))
 def test_binary(self):self.assertIsNotNone(text_issue(b'ELF\0binary'))
if __name__=='__main__':unittest.main()
