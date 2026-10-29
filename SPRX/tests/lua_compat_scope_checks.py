"""Run the actual compatibility require wrapper and check exact flag restoration."""
from pathlib import Path
import ast, re, subprocess, sys

root=Path(__file__).resolve().parents[2]
source=Path(sys.argv[2]).read_text() if len(sys.argv)>2 else (root/'SPRX/t7_lua.cpp').read_text()
block=source.split('static const char k_lobbyParityLua[] =',1)[1].split(';',1)[0]
chunk=''.join(ast.literal_eval(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"',block))
pc_block=source.split('static const char k_isPcLua[] =',1)[1].split(';',1)[0]
pc_chunk=''.join(ast.literal_eval(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"',pc_block))
fixture=r'''
local function scenario(initial,scope,fail)
  local env=setmetatable({}, {__index=_G})
  env._G=env
  env.CoD={isPC=initial}
  env.BO3CustomsPCScope=scope
  env.BO3CustomsModFiles={['test/module.lua']=true,['test/failing.lua']=true}
  local calls=0
  env.require=function(name)
    calls=calls+1
    if name=='test.module' or name=='test.failing' then assert(rawget(env.CoD,'isPC')==true) end
    if name=='test.failing' then error('expected import error') end
    return 'loaded'
  end
  local native=env.require
  local install=assert(loadstring(CHUNK));setfenv(install,env);install()
  assert(env.require~=native)
  local ok,value=pcall(env.require,fail and 'test.failing' or 'test.module')
  assert(rawget(env.CoD,'isPC')==initial,'PC flag was not restored exactly')
  assert(rawget(env,'BO3CustomsPCScope')==scope,'scope marker was not restored exactly')
  if fail then assert(not ok and tostring(value):find('expected import error')) else assert(ok and value=='loaded') end
  assert(calls==1)
  local wrapped=env.require;install();assert(env.require==wrapped)
  return env
end
scenario(false,nil,false)
scenario(false,nil,true)
scenario(false,false,false)
scenario(false,false,true)
scenario(nil,nil,false)
scenario(nil,nil,true)
local env=scenario(false,nil,false)
env.BO3CustomsModFiles={}
env.require('test.unowned');assert(rawget(env.CoD,'isPC')==false)
local env=setmetatable({}, {__index=_G});env._G=env
env.Engine={GetCurrentMap=function()return 'test_map'end}
env.CoD={isPC=false};env.BO3CustomsPreGame=1
local apply=assert(loadstring(PC_CHUNK));setfenv(apply,env);apply();assert(env.CoD.isPC==true)
env.BO3CustomsPreGame=0;apply();assert(rawget(env.CoD,'isPC')==false)
env.CoD={isPC=true};apply();assert(rawget(env.CoD,'isPC')==true,'old CoD state leaked into replacement table')
env.CoD=setmetatable({}, {__index={isPC=false}});apply();assert(rawget(env.CoD,'isPC')==nil)
env.BO3CustomsPreGame=1;apply();assert(rawget(env.CoD,'isPC')==true)
env.BO3CustomsPreGame=0;apply();assert(rawget(env.CoD,'isPC')==nil and env.CoD.isPC==false)
print('PASS: exact scoped state restoration and per-CoD ownership across frontend table replacement')
'''
subprocess.run([sys.argv[1],'-'],input='local CHUNK=[====['+chunk+']====]\nlocal PC_CHUNK=[====['+pc_chunk+']====]\n'+fixture,text=True,check=True)
