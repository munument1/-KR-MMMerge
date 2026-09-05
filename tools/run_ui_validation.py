"""Offline validation only; does not launch or modify a game installation."""
from pathlib import Path
import os, struct, subprocess, sys, tempfile
import lupa.lua51 as lupa
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
subprocess.run([sys.executable,'tools/validate_native_dbcs_integration.py','.'],check=True)
lua=lupa.LuaRuntime(encoding=None)
compile_lua=lua.eval(b'function(s) local f,e=loadstring(s); return f~=nil,e end')
count=0
for path in sorted((ROOT/'Scripts').rglob('*.lua')):
    ok,err=compile_lua(path.read_bytes())
    if not ok: raise RuntimeError(f'{path}: {err}')
    count+=1
print(f'PASS: Lua 5.1 syntax, {count} installed scripts',flush=True)
for path in (ROOT/'DataFiles').glob('DBCS_*.fnt'):
    data=path.read_bytes(); height=data[5]
    for c in range(256):
        width=struct.unpack_from('<i',data,0x24+12*c)[0]
        offset=struct.unpack_from('<i',data,0xc20+4*c)[0]
        if width>0 and (offset<0 or 0x1020+offset+width*height>len(data)):
            raise ValueError(f'{path.name}: glyph {c} outside file')
print('PASS: shipped page glyph bounds',flush=True)
tmp_root=ROOT/'.test-tmp'; tmp_root.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
    assert Path(tmp).resolve().parent == tmp_root.resolve()
    os.chdir(tmp); Path('Data').mkdir(); Path('Data/LocalizeConf.ini').write_text('[Settings]\nencoding=gb2312\n')
    lua=lupa.LuaRuntime(encoding=None)
    lua.globals().SCRIPT_UNDER_TEST=str(ROOT/'Scripts/General/FNT_DBCS.lua').replace('\\','/').encode()
    try:
        lua.execute((ROOT/'tools/fixtures/harness_mm8.lua').read_bytes())
    finally:
        os.chdir(ROOT)
subprocess.run([sys.executable,'-m','unittest','discover','-s','tools','-p','test_ui_safety.py','-v'],check=True)
print('PASS: offline validation complete; actual engine/GPU and long-play reproduction not tested',flush=True)
