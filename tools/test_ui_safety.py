"""Lua 5.1 regressions using the pinned harness and shipped Korean page bytes.
Run: python -m unittest discover -s tools -p test_ui_safety.py -v
The native code and GPU are simulated; these are not in-game reproduction tests.
"""
from pathlib import Path
import os
import struct
import tempfile
import unittest
import zlib
import lupa.lua51 as lupa

ROOT = Path(__file__).resolve().parents[1]
BOOT = (ROOT/'tools/fixtures/harness_mm8.lua').read_bytes().split(b'-- ===== load the real file =====')[0]

class LuaFixture(unittest.TestCase):
    def setUp(self):
        self.cwd = Path.cwd()
        self.tmp_root = ROOT/'.test-tmp'
        self.tmp_root.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=self.tmp_root)
        os.chdir(self.tmp.name)
        Path('Data').mkdir()
        Path('Data/LocalizeConf.ini').write_bytes((ROOT/'Data/LocalizeConf.ini').read_bytes())
        self.lua = lupa.LuaRuntime(encoding=None)
        self.lua.execute(BOOT)
        self.lua.globals().ASSET_ROOT = str(ROOT/'DataFiles').replace('\\','/').encode()
        self.lua.execute(br'''
            ASSET_LOADS = 0
            Game.LoadDataFileFromLod = function(name)
                ASSET_LOADS = ASSET_LOADS + 1
                local f = assert(io.open(ASSET_ROOT .. '/' .. name, 'rb'))
                local bytes = f:read('*all'); f:close()
                local p = 0x08000000 + ASSET_LOADS * 0x40000
                mem.copy(p, bytes)
                return p, #bytes
            end
            function put(s, p) p=p or 0x03000000; mem.copy(p,s..'\0'); return p end
            function wrap(s, width, font2)
                local dlg=0x04000000; mem.i4[dlg+8]=width or 400
                local fn=font2 and HF[0x44A058] or HF[0x449ECA]
                local def=function() return put('original-ascii',0x03500000) end
                if font2 then return fn.f(nil,def,put(s),FONT16,FONT16B,dlg,0,0) end
                return fn.f(nil,def,put(s),FONT16,dlg,0,0)
            end
        ''')
    def tearDown(self):
        os.chdir(self.cwd)
        assert Path(self.tmp.name).resolve().parent == self.tmp_root.resolve()
        self.tmp.cleanup()
    def load(self):
        self.lua.execute((ROOT/'Scripts/General/FNT_DBCS.lua').read_bytes())
    def runlua(self,s): return self.lua.execute(s)

class RendererTests(LuaFixture):
    def test_short_dbcs_keeps_original_buffer_and_ascii_fallback(self):
        self.load()
        self.assertEqual(self.runlua(br"return wrap('\176\161',400)"),0x5dc8e0)
        self.assertEqual(self.runlua(br"return mem.string(wrap('hello',400))"),b'original-ascii')
    def test_long_output_preserved_without_touching_adjacent_globals(self):
        self.load()
        self.assertTrue(self.runlua(br'''
            local base=0x5DC8E0; mem.copy(base+2048,string.rep('Z',2048))
            local original=string.rep('\176\161',1500)
            local p=wrap(original,100000)
            return p~=base and mem.string(p)==original and #mem.string(base)==2046
                and mem.string(base+2048)==string.rep('Z',2048)
        '''))
    def test_actual_shipped_history_body_is_preserved(self):
        self.load()
        data=(ROOT/'Data/zz LocKO.T.lod').read_bytes()
        ro,_,_,count=struct.unpack_from('<IIII',data,0x110)
        found=None
        for i in range(count):
            p=ro+i*76
            if data[p:p+64].split(b'\0')[0].lower()!=b'history.txt': continue
            off,size,_=struct.unpack_from('<III',data,p+64); rec=data[ro+off:ro+off+size]
            n=struct.unpack_from('<I',rec,68)[0]; raw=rec[96:96+n]
            if struct.unpack_from('<I',rec,88)[0]: raw=zlib.decompress(raw)
            found=raw.split(b'\r\n')[1].split(b'\t')[1]; break
        self.assertIsNotNone(found)
        self.lua.globals().TEXT=found
        self.assertTrue(self.runlua(br'''
            mem.u1[0x5DD0E0]=90
            local result=mem.string(wrap(TEXT,400))
            -- Existing spaces can become newlines; no content may disappear.
            return #result==#TEXT and result:gsub('\n',' ')==TEXT:gsub('\n',' ')
                and mem.u1[0x5DD0E0]==90
        '''))
    def test_long_ascii_cannot_fall_back_to_unbounded_engine_wrap(self):
        self.load()
        self.assertTrue(self.runlua(br'''
            mem.u1[0x5DD0E0]=90
            local text=string.rep('word ',600)
            local p=wrap(text,400)
            return p~=0x5DC8E0 and #mem.string(p)==#text and mem.u1[0x5DD0E0]==90
        '''))
    def test_both_wrap_functions_and_legacy_markers_use_bounded_mirror(self):
        self.load()
        self.assertTrue(self.runlua(br'''
            local marked=string.rep('\14\32\14\176\161\7\15',1400)
            for _,f2 in ipairs({false,true}) do
                mem.u1[0x5DD0E0]=90
                local p=wrap(marked,400,f2)
                assert(p~=0x5DC8E0 and #mem.string(p)>2047)
                assert(not mem.string(p):find('\14',1,true) and mem.u1[0x5DD0E0]==90)
            end
            return true
        '''))
    def test_null_and_carriage_return_contract(self):
        self.load()
        self.assertTrue(self.runlua(br'''
            local f=HF[0x449ECA].f
            assert(f(nil,function() error('fallback') end,0,FONT16,0,0,0)==0x5DC8E0)
            assert(mem.u1[0x5DC8E0]==0)
            local p=put('\176\161\13text')
            return f(nil,function() error('fallback') end,p,FONT16,0,0,0)==p
        '''))
    def test_owned_capacity_and_dbcs_boundary(self):
        self.load()
        self.assertTrue(self.runlua(br'''
            local p=wrap(string.rep('\176\161',3000),100000)
            local s=mem.string(p)
            return #s<=4095 and #s%2==0 and mem.u1[p+#s]==0
        '''))
    def test_cache_has_count_and_byte_bounds_and_evicted_values_recompute(self):
        self.load()
        self.assertTrue(self.runlua(br'''
            local first=DBCS.wrapText('\176\161 first',FONT16,nil,400,0)
            for i=1,4000 do DBCS.wrapText('\176\161 '..i,FONT16,nil,400,0) end
            collectgarbage('collect'); collectgarbage('collect')
            local c=DBCS.getWrapCacheStats()
            assert(c.entries<=256 and c.bytes<=512*1024)
            assert(DBCS.wrapText('\176\161 first',FONT16,nil,400,0)==first)
            for i=1,500 do DBCS.wrapText(string.rep('\176\161',1500)..i,FONT16,nil,400,0) end
            c=DBCS.getWrapCacheStats()
            return c.entries<256 and c.bytes<=c.maxBytes
        '''))
    def test_cache_cleared_on_load_even_if_save_migration_fails(self):
        self.load()
        self.assertTrue(self.runlua(br'''
            DBCS.wrapText('\176\161',FONT16,nil,400,0)
            assert(DBCS.getWrapCacheStats().entries==1)
            for _,fn in ipairs(events._AfterLoadMap) do fn() end
            return DBCS.getWrapCacheStats().entries==0
        '''))
    def test_lua_font_returnpointer_wrapper_preserves_full_byte_view(self):
        # Models RSMem's documented class method and byte-array lookup.
        self.lua.execute(br'''
            mem.struct=function(defineFn)
                return {new=function(self,p)
                    return {Bytes=setmetatable({['?ptr']=p}, {__index=function(_,k) return mem.u1[p+k] end})}
                end}
            end
            Game.WordWrappedTextBytes={['?ptr']=0x5DC8E0}
            structs={Fnt={WordWrap=function(self,s,dlg,x,keepR,returnPointer)
                local p=wrap(s,100000)
                return returnPointer and Game.WordWrappedTextBytes or mem.string(p)
            end}}
        ''')
        self.load()
        self.assertTrue(self.runlua(br'''
            local text=string.rep('\176\161',1500)
            local f=structs.Fnt.WordWrap
            local view=f({},text,nil,0,0,true)
            assert(view['?ptr']~=0x5DC8E0 and view[2999]==161 and view[3000]==0)
            assert(mem.string(view['?ptr'])==text and f({},text,nil,0,0,false)==text)
            return f({},'short',nil,0,0,true)==Game.WordWrappedTextBytes
        '''))
    def test_renderer_errors_observable_with_logging_disabled(self):
        self.load()
        self.assertTrue(self.runlua(br'''
            HF[0x449C7B].f(nil,function() return 23 end,nil,put('\176\161'))
            return DBCS.Diagnostics.errors>0 and #DBCS.Diagnostics.lastError>0
        '''))

class DiagnosticTests(LuaFixture):
    def load_diag(self, enabled=1,native=1, signature=True):
        Path('Data/KO_UIDiagnostics.ini').write_text(f'[Settings]\nEnabled={enabled}\nNativeBegin2D={native}\n')
        self.lua.execute(br'''
            mem.u4=mem.i4
            local old=mem.string
            mem.string=function(p,n,raw)
                if n then local out={}; for i=0,n-1 do out[#out+1]=string.char(mem.u1[p+i]) end; return table.concat(out) end
                return old(p)
            end
            TIME=10000; timeGetTime=function() return TIME end
            Map={Name='out02.odm'}; Game.CurrentScreen=0; Game.PatchOptions={UILayout='UI'}
            const={Keys={CTRL=17}}; CTRL=true; Keys={IsPressed=function() return CTRL end}
            mem.dll={psapi={}}
            mem.u1[0xF01A64]=0
        ''')
        if signature: self.lua.execute(br"mem.copy(0x4A2FF2,'\85\139\236\131\236\124')")
        self.lua.execute((ROOT/'Scripts/General/ZZ_KoreanUIDiagnostics.lua').read_bytes())
    def test_disabled_installs_nothing(self):
        self.load_diag(enabled=0)
        self.assertTrue(self.runlua(b'return KoreanUIDiagnostics==nil and HF[0x4A2FF2]==nil'))
        self.assertFalse(Path('KO_UI_Diagnostic.log').exists())
    def test_wrong_signature_skips_native_probe_but_keeps_event_diagnostics(self):
        self.load_diag(signature=False)
        self.assertTrue(self.runlua(b"return HF[0x4A2FF2]==nil and KoreanUIDiagnostics.NativeProbe=='skipped-entry-signature-mismatch'"))
        self.assertIn('skipped-entry-signature-mismatch',Path('KO_UI_Diagnostic.log').read_text())
    def test_native_wrapper_preserves_call_return_and_does_not_repair_failure(self):
        self.load_diag()
        self.assertTrue(self.runlua(br'''
            local n=0
            local result=HF[0x4A2FF2].f(nil,function(this) n=n+1; assert(this==0xEC1980); return 1234 end,0xEC1980)
            KoreanUIDiagnostics.Snapshot()
            return n==1 and result==1234 and mem.i4[0xF01A64]==0 and mem.i4[0xF01A6C]==0
        '''))
        self.assertIn('Begin2D-failed',Path('KO_UI_Diagnostic.log').read_text())
    def test_foreground_and_tick_are_distinguished(self):
        self.load_diag(native=0)
        self.runlua(br'''
            mem.i4[0xF01A64]=1
            for _,f in ipairs(events._FGInterfaceUpd) do f() end
            mem.i4[0xF01A64]=0
            TIME=20000; for _,f in ipairs(events._Tick) do f() end
        ''')
        log=Path('KO_UI_Diagnostic.log').read_text()
        self.assertIn('phase=FG-before-End2D',log)
        self.assertIn('phase=Tick-outside-draw',log)
    def test_mark_requires_exact_hotkey_and_ignores_repeat(self):
        self.load_diag(native=0)
        self.assertTrue(self.runlua(br'''
            local f=events._KeyDown[1]
            f({Key=121,Alt=false,WasPressed=false})
            f({Key=121,Alt=true,WasPressed=true})
            local t={Key=121,Alt=true,WasPressed=false}; f(t)
            return t.Handled==true
        '''))
        self.assertEqual(Path('KO_UI_Incident.log').read_text().count('=== USER MARK'),1)
    def test_logs_rotate_and_remain_bounded(self):
        self.load_diag(native=0)
        Path('KO_UI_Diagnostic.log').write_bytes(b'x'*(2*1024*1024))
        self.runlua(b'KoreanUIDiagnostics.Snapshot()')
        self.assertTrue(Path('KO_UI_Diagnostic.log.previous').exists())
        self.assertLess(Path('KO_UI_Diagnostic.log').stat().st_size,2*1024*1024)
    def test_logger_exception_does_not_change_original_call(self):
        self.load_diag()
        self.assertTrue(self.runlua(br'''
            timeGetTime=function() error('clock failure') end
            -- The logger captured its clock; force state snapshot's date to fail.
            os.date=function() error('date failure') end
            TIME=20000
            return HF[0x4A2FF2].f(nil,function() return 42 end,0xEC1980)==42
        '''))

if __name__=='__main__': unittest.main()
