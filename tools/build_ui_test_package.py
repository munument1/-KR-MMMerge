"""Build local test ZIPs only. No install, upload, tagging, or release actions."""
from pathlib import Path
import hashlib, os, subprocess, sys, zipfile
sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'; OUT.mkdir(exist_ok=True)
result=subprocess.run([sys.executable,str(ROOT/'tools/run_ui_validation.py')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONIOENCODING="utf-8"))
(OUT/'VALIDATION.txt').write_bytes(result.stdout)
if result.returncode: print(result.stdout.decode('utf-8',errors='replace')); raise SystemExit(result.returncode)
common={'README.txt':(ROOT/'UI_TEST1_README.txt').read_bytes(),'UI_TEST1_NOTES.md':(ROOT/'UI_TEST1_NOTES.md').read_bytes()}
diag=dict(common)
for name in ['Data/KO_UIDiagnostics.ini','Scripts/General/ZZ_KoreanUIDiagnostics.lua']:
    diag[name]=(ROOT/name).read_bytes()
full=dict(common)
for folder in ['Data','DataFiles','Scripts','licenses']:
    for path in (ROOT/folder).rglob('*'):
        if path.is_file(): full[path.relative_to(ROOT).as_posix()]=path.read_bytes()
full['FONT_LICENSES.md']=(ROOT/'FONT_LICENSES.md').read_bytes()
full['CHANGELOG.txt']=b'UI investigation test1: see README.txt and UI_TEST1_NOTES.md.\r\n\r\n'+(ROOT/'CHANGELOG.txt').read_bytes()
for suffix,files in [('DiagnosticsOnly',diag),('FullTest',full)]:
    sums=''.join(f'{hashlib.sha256(b).hexdigest()}  {n}\n' for n,b in sorted(files.items()))
    files['SHA256SUMS.txt']=sums.encode('utf-8')
    name=f'MMMerge_Korean_v1.0.15_UI_test1_{suffix}.zip'
    target=OUT/name
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(files.items()):
            info=zipfile.ZipInfo(n,(2026,9,5,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,b,compresslevel=9)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            sha,n=line.split('  ',1); assert hashlib.sha256(z.read(n)).hexdigest()==sha,n
        assert not any(n.lower().endswith(('.exe','.dll','.mm8')) or n.startswith('Saves/') for n in z.namelist())
        if suffix=='DiagnosticsOnly': assert 'Scripts/General/FNT_DBCS.lua' not in z.namelist()
        else:
            assert z.read('Scripts/General/FNT_DBCS.lua')==(ROOT/'Scripts/General/FNT_DBCS.lua').read_bytes()
            assert sum(n.startswith('DataFiles/DBCS_') for n in z.namelist())==104
    sha=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(f'{sha}  {name}\n',encoding='ascii')
    print(f'{name}: {len(files)} files, {target.stat().st_size:,} bytes, SHA256 {sha}')
print('Validated both ZIP manifests and contents. Logs: dist/VALIDATION.txt')
