-- FNT_DBCS.lua -- native (marker-free) DBCS rendering for MM8 / MM Merge (GrayFace Patch + MMExtension)
-- Plain GB2312/GBK/Big5/EUC bytes in game text render directly with DBCS page fonts;
-- word wrap can break after any CJK character, with basic kinsoku punctuation rules.
--
-- Activation: automatic whenever Data/LocalizeConf.ini's [Settings] encoding
-- is a supported DBCS encoding. Optional [Settings] keys (legacy page-font
-- path and debugging; none are written into shipped inis unless needed):
--   fontSizes=14,16,29          page font heights when they differ from the
--                               13,16,29 default (DBCS_<h>_<hi>.fnt)
--   specialFonts=Autonote:15b   per-original-font page override
--   nativedemo=1                debug: show a plain-DBCS test message in-game
--   nativelog=1                 debug: write FNT_DBCS.log diagnostics
-- BDF font mappings live in the [dbcsFont] section (see below).
--
-- MM7 and MM8 engines (addresses per engine in the ENGINES table; frame
-- layouts of all five per-char loops are identical between the two).
-- Patches (design doc "原生 DBCS 渲染方案"):
--   B  GetLineWidth      full Lua replacement, DBCS-aware measuring
--   C  WordWrap          full Lua replacement, CJK breaks + kinsoku
--   C' WordWrap2         same + '_' second-font semantics (scrolls)
--   M  Draw/DrawTextLimited entries decode legacy marker text (direct-draw paths)
--   L  3x push-eax + 1 asmhook    consumers measure the *wrapped* buffer length
--                                 (our wrap may change text length; engine's never did)
--   D  DrawText loop     consume pair, blit DBCS glyph directly
--   E  DrawTextLimited truncate + inline draw loops
--   F  scroll line renderer (blit into 16bpp buffer)
--   G  centered line renderer
--   A  TestChar          accept bytes >= leadMin as valid (pure asm)
--   A2 (MM7 only) same for the validity test inlined in MM7's Draw loop
-- A/A2 install LAST and only if everything else succeeded: with A active but a
-- draw loop unpatched, the engine would fetch SBCS glyphs for lead bytes (garbage
-- offsets -> possible access violation), so partial installs must never enable A.
-- Legacy marker text ([SO]..[SI], e.g. old savegames) is decoded on the fly.
--
-- By Tom CHEN <tomchen.org>, MIT/Expat License

local mmver = offsets.MMVersion

-- ============ SETTINGS FROM INI ============

local globalEncoding, nativeDemo
local logEnabled = false
local lineSpacing = 0 -- extra px between text lines (engine default = fontHeight-3)
local fontSizes = {13, 16, 29}
local specialFonts = {Autonote = {15, "b"}}
local iniFonts = {} -- the [dbcsFont] section, raw values

-- section-aware ini parser: keys only count inside their [section]
local function parseIni(content)
	local sections = {}
	local cur
	for line in content:gmatch("[^\r\n]+") do
		if not line:match("^%s*[;#]") then
			local sec = line:match("^%s*%[([^%]]+)%]")
			if sec then
				cur = sections[sec] or {}
				sections[sec] = cur
			elseif cur then
				local k, v = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
				if k then
					cur[k] = v
				end
			end
		end
	end
	return sections
end

do
	local fs = io.open("Data/LocalizeConf.ini", "r")
	if fs then
		local raw = fs:read("*all")
		fs:close()
		local ini = parseIni(raw)
		local st = ini.Settings or {}
		globalEncoding = st.encoding
		nativeDemo = st.nativedemo == "1" -- debug helpers, not part of shipped inis
		logEnabled = st.nativelog == "1"
		lineSpacing = tonumber(st.lineSpacing) or 0
		if lineSpacing < 0 then
			lineSpacing = 0
		elseif lineSpacing > 10 then
			lineSpacing = 10 -- keep dialogs from growing absurdly tall
		end
		if st.fontSizes and st.fontSizes ~= "" then
			fontSizes = {}
			for n in st.fontSizes:gmatch("%d+") do
				fontSizes[#fontSizes + 1] = tonumber(n)
			end
			table.sort(fontSizes)
		end
		if st.specialFonts and st.specialFonts ~= "" then
			specialFonts = {}
			for name, h, tag in st.specialFonts:gmatch("(%w+):(%d+)(%a*)") do
				specialFonts[name] = {tonumber(h), tag}
			end
		end
		iniFonts = ini.dbcsFont or {}
	end
end

-- lead byte ranges per encoding; lo = valid trail byte ranges.
-- shift_jis note: single-byte half-width katakana (0xA1-0xDF) is NOT
-- supported (those bytes are treated as lead-byte candidates and skipped);
-- Japanese text must use full-width kana.
local encProps = {
	gb2312    = {leadMin = 0xA1, hi = {{0xA1, 0xA9}, {0xB0, 0xF7}}, lo = {{0xA0, 0xFE}}},
	gbk       = {leadMin = 0x81, hi = {{0x81, 0xFE}}, lo = {{0x40, 0x7E}, {0x80, 0xFE}}},
	big5      = {leadMin = 0xA1, hi = {{0xA1, 0xC7}, {0xC9, 0xF9}}, lo = {{0x40, 0x7E}, {0xA0, 0xFE}}},
	shift_jis = {leadMin = 0x81, hi = {{0x81, 0x9F}, {0xE0, 0xFC}}, lo = {{0x40, 0x7E}, {0x80, 0xFC}}},
	euc_kr    = {leadMin = 0xA1, hi = {{0xA1, 0xAC}, {0xB0, 0xC8}, {0xCA, 0xFD}}, lo = {{0xA0, 0xFE}}},
}
local enc = globalEncoding and encProps[globalEncoding]

if (mmver < 6 or mmver > 8) or not enc then
	return
end

-- ============ DIAGNOSTIC LOG ============

local function dlog(msg)
	if not logEnabled then
		return
	end
	local f = io.open("FNT_DBCS.log", "a")
	if f then
		f:write(os.date("%H:%M:%S "), msg, "\n")
		f:close()
	end
end

local loggedOnce = {}
local function dlogOnce(key, msg)
	if not loggedOnce[key] then
		loggedOnce[key] = true
		dlog(msg)
	end
end

dlog("=== FNT_DBCS start: encoding=" .. tostring(globalEncoding)
	.. " sizes=" .. table.concat(fontSizes, ",") .. " demo=" .. tostring(nativeDemo))

-- ============ LOCALS / ENGINE ADDRESSES (MM8 only) ============

local u1, u2, i4 = mem.u1, mem.u2, mem.i4
local call, copy, memstr = mem.call, mem.copy, mem.string
local floor, byte, format = math.floor, string.byte, string.format

-- per-engine address tables. Shared facts (verified by disassembly of both
-- exes): the five per-char loops have IDENTICAL frame layouts in MM7 and MM8;
-- only addresses, blitters, buffers and the D-loop char register differ.
-- Loop spec fields: anchor/size = patched original bytes, reg = register the
-- stub compares against leadMin, cont = loop-continue address the DBCS path
-- jumps to, orig = displaced original instructions (fallthrough returns to
-- anchor+size via asmpatch), char = how the handler reads the lead byte
-- ("cl" / "eax" clean / "eaxlow" = al with dirty upper bytes).
local ENGINES = {
	[8] = {
		TestChar        = 0x449C3B, -- per-char validity predicate (9-byte patch site)
		TestCharValid   = 0x449C5B,
		TestCharInvalid = 0x449C44,
		GetLineWidth    = 0x449C7B, -- fastcall(font, str)
		WordWrap        = 0x449ECA, -- fastcall(str, font; dlg, x, keepR) -> WrapBuf
		WordWrap2       = 0x44A058, -- fastcall(str, font; font2, dlg, x, keepR)
		Draw            = 0x44A50F, -- fastcall(dlg, font; x, y, color, str, opaque, bottom, shadow)
		DrawTextLimited = 0x44A253, -- fastcall(dlg, font; x, y, color, str, w, right)
		WrapBuf         = 0x5DC8E0, -- Game.WordWrappedText, 2048 bytes
		-- "fontHeight-3" line-spacing sites (byte-scanned): immediate bytes of
		-- lea reg,[reg+fh-3] (0xFD) and sub reg,3 (0x03) in the text cluster
		LineLea         = {0x449D8B, 0x449E20, 0x449EAB, 0x44A4C3, 0x44A4CA, 0x44A737, 0x44A754},
		LineSub         = {0x449D20, 0x449DAC, 0x44AAC2},
		LtdBuf          = 0x5E1020, -- shared scratch used by DrawTextLimited
		Screen          = 0xEC1980, -- screen object ("this" of the glyph blitters)
		BlitGlyph       = 0x4A4D01, -- thiscall(screen; x, y, glyph, w, h, pal, opaque)
		BlitGlyphShadow = 0x4A4E9F, -- thiscall(screen; x, y, glyph, w, h, pal, color, shadow)
		BlitGlyphToBuf  = 0x410AA5, -- fastcall(dest, glyph; w, h, pal, color, pitch*2)
		Strlen          = 0x4DA190,
		Cap = 4095,         -- WordWrappedText is nominally 2048 bytes, but the
		                    -- vanilla ENGLISH history texts already make the
		                    -- original in-place wrap write up to 3709 bytes
		                    -- there (entry 1) - so up to 4095 is no worse than
		                    -- what the vanilla game does on every history view
		L1 = {0x449D26, 1}, -- GetTextHeight:  push ebx      -> push eax (wrap result)
		L2 = {0x449DB8, 3}, -- GetTextHeight2: push [ebp+8]  -> push eax
		L3 = {0x449E4C, 1}, -- PageBreak:      push esi      -> push eax
		L4 = 0x44A593,      -- Draw: recompute [ebp-0xC] len after the wrap call
		loops = {
			D  = {anchor = 0x44A5FB, size = 5, reg = "cl", cont = 0x44A79C, char = "cl",
				orig = "cmp cl, 0x22\njne absolute 0x44A610"},
			E1 = {anchor = 0x44A2F5, size = 6, reg = "cl", cont = 0x44A320, char = "cl",
				orig = "cmp dword [ebp+0x14], 0\njle absolute 0x44A306"},
			E2 = {anchor = 0x44A3B8, size = 8, reg = "al", cont = 0x44A4F3, char = "eax",
				orig = "cmp dword [ebp+0x14], 0\nlea ecx, [eax+eax*2+9]"},
			F  = {anchor = 0x44A830, size = 7, reg = "al", cont = 0x44A8CE, char = "eax",
				orig = "lea ecx, [eax+eax*2+9]\nmov ebx, [esi+ecx*4]"},
			G  = {anchor = 0x44A953, size = 7, reg = "al", cont = 0x44A9EB, char = "eax",
				orig = "lea ecx, [eax+eax*2+9]\nmov edx, [esi+ecx*4]"},
		},
	},
	[7] = {
		TestChar        = 0x44C50A,
		TestCharValid   = 0x44C52A,
		TestCharInvalid = 0x44C513,
		GetLineWidth    = 0x44C54A,
		WordWrap        = 0x44C794,
		WordWrap2       = 0x44C95F,
		Draw            = 0x44CE34,
		DrawTextLimited = 0x44CB7B,
		WrapBuf         = 0x5C4430,
		LineLea         = {0x44C657, 0x44C6EB, 0x44C775, 0x44CDE8, 0x44CDEF, 0x44D068, 0x44D085},
		LineSub         = {0x44C5ED, 0x44C675, 0x44D40A},
		LtdBuf          = 0x5C6400,
		Screen          = 0xDF1A68,
		BlitGlyph       = 0x4A6A41,
		BlitGlyphShadow = 0x4A6BDF,
		BlitGlyphToBuf  = 0x40F851,
		Strlen          = 0x4CAFF0,
		Cap = 2047,
		L1 = {0x44C5F6, 1},
		L2 = {0x44C686, 3},
		L3 = {0x44C719, 1},
		L4 = 0x44CEC4,
		-- MM7's Draw inlines the char-validity test instead of calling TestChar,
		-- so it needs its own accept-lead-bytes patch (A2)
		A2 = {anchor = 0x44CEF7, size = 7, valid = 0x44CF14, invalid = 0x44CF00},
		loops = {
			D  = {anchor = 0x44CF36, size = 7, reg = "al", cont = 0x44D0CA, char = "eaxlow",
				orig = "cmp al, 0x22\njne absolute 0x44CF48\nmov eax, [ebp-4]"},
			E1 = {anchor = 0x44CC1D, size = 6, reg = "cl", cont = 0x44CC46, char = "cl",
				orig = "cmp dword [ebp+0x14], 0\njle absolute 0x44CC2D"},
			E2 = {anchor = 0x44CCDD, size = 8, reg = "al", cont = 0x44CE18, char = "eax",
				orig = "cmp dword [ebp+0x14], 0\nlea ecx, [eax+eax*2+9]"},
			F  = {anchor = 0x44D15E, size = 7, reg = "al", cont = 0x44D1FC, char = "eax",
				orig = "lea ecx, [eax+eax*2+9]\nmov ebx, [esi+ecx*4]"},
			G  = {anchor = 0x44D280, size = 7, reg = "al", cont = 0x44D318, char = "eax",
				orig = "lea ecx, [eax+eax*2+9]\nmov edx, [esi+ecx*4]"},
		},
	},
	[6] = {
		-- MM6: no shared TestChar (the validity test is inlined in every loop,
		-- so each loop patch diverts lead bytes BEFORE its inline test and no
		-- A patch exists), no WordWrap2/scroll-font2, no GetTextHeight2 /
		-- PageBreak. WordWrap takes only (dlg, x) and its buffer is 4096 bytes.
		-- Rendering: 16bpp framebuffer walked by pointer; pitch comes from the
		-- scanline offset table. Blitters are fastcall(destPixels, glyph; ...).
		GetLineWidth    = 0x442DD0, -- fastcall(font, str)
		WordWrap        = 0x442F50, -- fastcall(str, font; dlg, x) -> WrapBuf
		Draw            = 0x4435F0, -- fastcall(dlg, font; x, y, color, str)
		DrawTextLimited = 0x443210, -- fastcall(dlg, font; x, y, color, str, w, right)
		WrapBuf         = 0x55BDE0,
		Cap             = 4095,     -- MM6 wrap buffer is 4096 incl. NUL
		LtdBuf          = 0x55D5B0,
		BlitPlain       = 0x40AA60, -- fastcall(destPixels, glyph; w, h, pal)
		BlitColored     = 0x40AAB0, -- fastcall(destPixels, glyph; w, h, pal, color)
		BlitToBuf       = 0x40AB10, -- fastcall(destPixels, glyph; w, h, pal, color, pitch*2)
		RowTable        = 0x4CA718, -- scanline offset table (pitch = row[1]-row[0])
		LineLea         = {0x442F1D, 0x443513, 0x443801},
		LineSub         = {0x442EBA, 0x443B14},
		L1 = {0x442EC0, 5, "mov edx, eax\nmov edi, eax\nor ecx, -1"}, -- strlen the wrap result
		L4 = 0x44368D,
		loops = {
			D  = {anchor = 0x4436D6, size = 7, reg = "al", cont = 0x4438BC, char = "eaxlow",
				orig = "cmp al, cl\njb absolute 0x4436DF\ncmp al, [ebp+1]"},
			E1 = {anchor = 0x44330B, size = 8, reg = "al", cont = 0x44335E, char = "eaxlow",
				orig = "cmp al, [ebp]\njb absolute 0x443315\ncmp al, [ebp+1]"},
			E2 = {anchor = 0x4433ED, size = 7, reg = "al", cont = 0x443597, char = "eaxlow",
				orig = "cmp al, cl\njb absolute 0x4433F6\ncmp al, [ebp+1]"},
			G  = {anchor = 0x44393B, size = 7, reg = "al", cont = 0x443A07, char = "eaxlow",
				orig = "cmp al, cl\njb absolute 0x443944\ncmp al, [esi+1]"},
		},
	},
}
local ADDR = ENGINES[mmver]
local WRAP_CAP = ADDR.Cap

local leadMin = enc.leadMin

local function inRanges(v, ranges)
	for i = 1, #ranges do
		local r = ranges[i]
		if v >= r[1] and v <= r[2] then
			return true
		end
	end
	return false
end

local function validHi(b)
	return inRanges(b, enc.hi)
end

local function validLo(b)
	return inRanges(b, enc.lo)
end

-- ============ .FNT ACCESS ============
-- layout: [0] MinChar, [1] MaxChar, [5] Height, [0xC] palette ptr,
-- ABC triplets (spaceBefore, width, spaceAfter) at +0x20 (12 bytes per char),
-- glyph offsets at +0xC20, glyph data at +0x1020

local function fntHeight(f)
	return u1[f + 5]
end

local function fntABC(f, c)
	local p = f + 0x20 + 12 * c
	return i4[p], i4[p + 4], i4[p + 8]
end

local function fntGlyph(f, c)
	return f + i4[f + 0xC20 + 4 * c] + 0x1020
end

-- per-SBCS-font metrics cache; revalidated on use because the engine may reload
-- resources (e.g. after alt-tab surface loss) leaving cached pointers stale
local fontM = {}
local function getFontM(font)
	local m = fontM[font]
	if m and (u1[font] ~= m.min or u1[font + 1] ~= m.max or fntHeight(font) ~= m.h) then
		m = nil -- same address, different content: rebuild
	end
	if not m then
		m = {min = u1[font], max = u1[font + 1], h = fntHeight(font), pal = i4[font + 0xC], abc = {}}
		fontM[font] = m
	end
	return m
end

local function getABC(m, font, c)
	local t = m.abc[c]
	if not t then
		local a, b, sa = fntABC(font, c)
		t = {a, b, sa}
		m.abc[c] = t
	end
	return t
end

-- which DBCS page font size a given original font uses
local replInfo = {}
local function getReplInfo(font)
	local ri = replInfo[font]
	if ri and ri.h == fntHeight(font) then
		return ri
	end
	local h = fntHeight(font)
	local size, deco
	for name, sf in pairs(specialFonts) do
		if Game[name .. "_fnt"] == font then
			size, deco = sf[1], sf[2]
		end
	end
	if not size then
		deco = ""
		size = fontSizes[1]
		for i = 2, #fontSizes do
			if h >= fontSizes[i] then
				size = fontSizes[i]
			end
		end
	end
	ri = {tag = tostring(size) .. deco, h = h}
	replInfo[font] = ri
	dlog(format("font %X h=%d -> DBCS size %s", font, h, ri.tag))
	return ri
end

-- DBCS page font loading (one .fnt per high byte per size), cached; false = failed
local canLoadProbe
do
	local ok, f = pcall(function() return Game.CanLoadFileFromLod end)
	canLoadProbe = ok and f or nil
end

-- a page entry remembers a few header bytes captured at load time; if they no
-- longer match, the engine has evicted/reused that memory and we must reload
local function pageAlive(pi)
	return u1[pi.addr + 5] == pi.h and u1[pi.addr] == pi.b0 and u1[pi.addr + 1] == pi.b1
end

local pages = {}
local function getPage(tag, hi)
	local t = pages[tag]
	if not t then
		t = {}
		pages[tag] = t
	end
	local pi = t[hi]
	if pi and not pageAlive(pi) then
		dlog(format("page DBCS_%s_%02X evicted, reloading", tag, hi))
		pi = nil
	end
	if pi == nil then
		local name = format("DBCS_%s_%02X.fnt", tag, hi)
		local p
		if canLoadProbe and not canLoadProbe(name) then
			p = false
		else
			local ok, r = pcall(Game.LoadDataFileFromLod, name)
			p = ok and tonumber(r) or false
			if p and (fntHeight(p) < 1 or fntHeight(p) > 64) then
				p = false
			end
		end
		if p then
			pi = {addr = p, h = fntHeight(p), b0 = u1[p], b1 = u1[p + 1]}
			t[hi] = pi
			dlog(name .. format(" ok @%X h=%d", p, fntHeight(p)))
		else
			-- a failure may be transient (load attempted during a resource reload):
			-- retry on later uses, give up for good only after several failures
			local fails = (t["fails" .. hi] or 0) + 1
			t["fails" .. hi] = fails
			pi = false
			if fails >= 3 then
				t[hi] = false
			end
			dlog(name .. " FAILED (attempt " .. fails .. ")")
		end
	end
	return pi
end

-- ============ BDF FONT MODE ============
-- Instead of pre-generated DBCS_<size>_<hi>.fnt page fonts, glyphs can come
-- from BDF files in Data\DBCSFonts\, mapped per engine font in the ini's
-- [dbcsFont] section:
--   [dbcsFont]
--   Arrus=wqy16.bdf          (style auto-detected from the game font's own
--                             glyphs: shadow / glow / plain / black - so
--                             Autonote comes out black, Spell plain,
--                             Book/Book2 glow, the rest shadow)
--   Comic=wqy16.bdf,plain    (an explicit shadow/glow/plain/black flag
--                             overrides the detection)
--   Smallnum=fusion12.bdf,2  (integer = extra line spacing for THIS font in
--                             pixels, 0-10: the engine font is heightened and
--                             its glyphs repadded at runtime, so lines of this
--                             font sit N px further apart - all other fonts
--                             keep their spacing; see [Settings] lineSpacing
--                             for the global knob)
--   Default=wqy12.bdf,wqy13.bdf,wqy16.bdf
-- Named mappings are fully explicit. The Default line takes one or more BDF
-- files; any font without its own line picks from them BY HEIGHT (largest BDF
-- that fits the font height, else the smallest) - same rule the page-font
-- path uses. Blank canvas rows a BDF declares above/below its actual ink (its
-- "ink band", measured across all glyphs at load) are always cropped away and
-- the glyph is bottom-anchored one row below the host font's baseline
-- (sampled from its own 0-9/A-Z glyphs), so CJK lines up with Latin text
-- automatically. BDF glyphs are keyed by Unicode; Data\DBCSFonts\<enc>.tbl
-- (generated by tools/gen_dbcstbl.py) maps DBCS pairs to code points.
-- Converted glyphs live in memory we own, so the engine can never evict
-- them. Fonts without any mapping use the legacy page path.

local FONTNAMES = {"Lucida", "Smallnum", "Arrus", "Create", "Comic", "Book",
	"Book2", "Cchar", "Autonote", "Spell"}

-- empty-value lines (the documented ini template's placeholders) mean
-- "not configured"
local bdfMap = {}
for name, spec in pairs(iniFonts) do
	if not spec:match("^%s*$") then
		-- style nil = auto-detect from the host game font's own glyphs;
		-- an explicit flag (shadow/plain/black) overrides the detection.
		-- adj = per-font extra line spacing in pixels (nil/0 = none)
		local files, style, adj = {}, nil, nil
		for tok in spec:gmatch("[^,%s]+") do
			if tok == "plain" or tok == "black" or tok == "shadow" or tok == "glow" then
				style = tok
			elseif tok:match("^[+%-]?%d+$") then
				adj = tonumber(tok) -- extra line spacing for this font
			else
				files[#files + 1] = tok
			end
		end
		if #files > 0 then
			if name == "Default" then
				bdfMap.Default = {files = files, style = style, adj = adj}
			else
				bdfMap[name] = {file = files[1], style = style, adj = adj}
			end
		end
	end
end

-- height of a BDF (header peek only; full load is deferred until a glyph is
-- actually needed from it); false = unusable
local bdfHeights = {}
local function bdfHeight(file)
	local h = bdfHeights[file]
	if h ~= nil then
		return h or nil
	end
	local f = io.open("Data/DBCSFonts/" .. file, "rb")
	if not f then
		dlog("BDF " .. file .. " MISSING")
		bdfHeights[file] = false
		return nil
	end
	local head = f:read(2048) or ""
	f:close()
	local _, fh = head:match("FONTBOUNDINGBOX (%-?%d+) (%-?%d+)")
	fh = tonumber(fh)
	if not fh or fh < 4 or fh > 64 then
		dlog("BDF " .. file .. " has no usable FONTBOUNDINGBOX")
		bdfHeights[file] = false
		return nil
	end
	bdfHeights[file] = fh
	return fh
end

-- DBCS pair -> Unicode, via the flat u16 table (0 = unmapped)
local uniData, hiIdx, loIdx, loCount
local function toUnicode(hi, lo)
	if uniData == nil then
		hiIdx, loIdx, loCount = {}, {}, 0
		for _, r in ipairs(enc.lo) do
			for b = r[1], r[2] do
				loIdx[b] = loCount
				loCount = loCount + 1
			end
		end
		local n = 0
		for _, r in ipairs(enc.hi) do
			for b = r[1], r[2] do
				hiIdx[b] = n
				n = n + 1
			end
		end
		local f = io.open("Data/DBCSFonts/" .. globalEncoding .. ".tbl", "rb")
		uniData = f and f:read("*all") or false
		if f then
			f:close()
		end
		dlog("unicode table " .. (uniData and format("loaded (%d bytes)", #uniData) or "MISSING"))
	end
	if not uniData then
		return nil
	end
	local h2, l2 = hiIdx[hi], loIdx[lo]
	if not h2 or not l2 then
		return nil
	end
	local p = (h2 * loCount + l2) * 2
	if p + 2 > #uniData then
		return nil
	end
	local b1, b2 = byte(uniData, p + 1, p + 2)
	local cp = b1 + b2 * 256
	if cp == 0 then
		return nil
	end
	return cp
end

local bdfFonts = {}
local function loadBdf(file)
	local obj = bdfFonts[file]
	if obj ~= nil then
		return obj
	end
	local f = io.open("Data/DBCSFonts/" .. file, "rb")
	if not f then
		dlog("BDF " .. file .. " MISSING")
		bdfFonts[file] = false
		return false
	end
	local s = f:read("*all")
	f:close()
	local _, fh, _, fy = s:match("\nFONTBOUNDINGBOX (%-?%d+) (%-?%d+) (%-?%d+) (%-?%d+)")
	fh, fy = tonumber(fh), tonumber(fy)
	if not fh or fh < 4 or fh > 64 then
		dlog("BDF " .. file .. " has no usable FONTBOUNDINGBOX")
		bdfFonts[file] = false
		return false
	end
	local idx = {}
	local n = 0
	local pos = 1
	while true do
		local _, e, cp = s:find("\nENCODING (%d+)", pos)
		if not e then
			break
		end
		idx[tonumber(cp)] = e + 1
		n = n + 1
		pos = e
	end
	-- some fonts position every glyph against a baseline their header lies
	-- about (e.g. zhenggedianhei: FONT_ASCENT = height, yet full-height
	-- glyphs carry by=-4 and small ones like U+4E00 carry the same offset).
	-- Heal it font-wide: the 99th-percentile bottom overflow is how far the
	-- glyph population really descends past the canvas; shifting the
	-- baseline up by that amount restores every glyph's designed position
	-- (honest fonts measure 0 and are untouched).
	local base = fh + fy
	local gBhs, gBys, overs = {}, {}, {}
	for bhS, byS in s:gmatch("\nBBX %-?%d+ (%-?%d+) %-?%d+ (%-?%d+)") do
		local bh, by = tonumber(bhS), tonumber(byS)
		if bh and bh > 0 then
			gBhs[#gBhs + 1] = bh
			gBys[#gBys + 1] = by
			local over = (base - by) - fh
			overs[#overs + 1] = over > 0 and over or 0
		end
	end
	if #overs > 0 then
		table.sort(overs)
		-- median of the positive overflows, applied only when at least half
		-- the glyph population overflows (a font-wide metadata lie); a few
		-- stray broken glyphs are left to the per-glyph clamp instead
		local firstPos
		for i = 1, #overs do
			if overs[i] > 0 then
				firstPos = i
				break
			end
		end
		if firstPos and (#overs - firstPos + 1) * 2 >= #overs then
			local heal = overs[floor((firstPos + #overs) / 2)]
			if heal > 0 then
				base = base - heal
				dlog(format("BDF %s: baseline healed by -%d (declared metrics off)", file, heal))
			end
		end
	end
	-- the font's ink band (1-based canvas rows): where its glyphs actually put
	-- pixels, using the same placement/clamping the builder applies. Pixel
	-- fonts draw nearly every glyph on one design box - if a single
	-- (top,bottom) extent covers >= 2/3 of the glyphs, that is the band
	-- (stray oversized symbols can't inflate it); otherwise (rasterized
	-- fonts with per-glyph extents) use the union so nothing gets clipped.
	local freq, total = {}, 0
	local tops, bots = {}, {}
	for i = 1, #gBhs do
		local bh, by = gBhs[i], gBys[i]
		local top = base - (by + bh)
		if top + bh > fh then
			top = fh - bh
		end
		if top < 0 then
			top = 0
		end
		local bot = top + bh
		if bot > fh then
			bot = fh
		end
		local key = top * 256 + bot
		freq[key] = (freq[key] or 0) + 1
		total = total + 1
		tops[#tops + 1] = top + 1
		bots[#bots + 1] = bot
	end
	local bandTop, bandBot = 1, fh
	if total > 0 then
		local bestKey, bestN = nil, 0
		for key, cnt in pairs(freq) do
			if cnt > bestN then
				bestKey, bestN = key, cnt
			end
		end
		if bestN * 3 >= total * 2 then
			bandTop = floor(bestKey / 256) + 1
			bandBot = bestKey % 256
		else
			-- no dominant design box (per-glyph extents vary): use the 1%/99%
			-- percentile envelope so a handful of oversized fringe glyphs
			-- can't stretch the band (e.g. Galmuri's 22-row canvas would
			-- otherwise swallow its 14px hangul design whole)
			table.sort(tops)
			table.sort(bots)
			local trim = floor(total * 0.01)
			bandTop = tops[1 + trim]
			bandBot = bots[total - trim]
		end
	end
	obj = {data = s, idx = idx, h = fh, base = base, bandTop = bandTop, bandBot = bandBot}
	bdfFonts[file] = obj
	dlog(format("BDF %s loaded: h=%d, %d glyphs, ink band %d-%d", file, fh, n, bandTop, bandBot))
	return obj
end

-- build one glyph in the engine's format. Styles (from the shipped fonts'
-- actual pixel conventions): "shadow" = body 255 + value-1 pixels offset
-- (+1,+1); "glow" = value-1 outline on all four sides (Book/Book2);
-- "plain" = body 255 only (e.g. Spell); "black" = body value 1 only
-- (e.g. Autonote). The glyph is placed on the BDF's declared canvas,
-- then only the font's ink band is emitted (blank canvas rows above/below
-- the ink are always cropped; shadow style keeps one extra row so the
-- bottom row's drop shadow survives). Vertical placement inside the host
-- font's line happens in getCJK (bottom gap).
local function bdfBuildGlyph(obj, cp, style)
	local pos = obj.idx[cp]
	if not pos then
		return nil
	end
	local s = obj.data
	local stop = s:find("ENDCHAR", pos, true)
	local chunk = s:sub(pos, stop or pos + 600)
	local dx = tonumber(chunk:match("DWIDTH (%-?%d+)"))
	local bw, bh, bx, by = chunk:match("BBX (%-?%d+) (%-?%d+) (%-?%d+) (%-?%d+)")
	bw, bh, bx, by = tonumber(bw), tonumber(bh), tonumber(bx), tonumber(by)
	local bitmapPos = chunk:find("BITMAP", 1, true)
	if not bw or not bitmapPos then
		return nil
	end
	local h = obj.h
	local w = dx or obj.h
	if w < bw + bx then
		w = bw + bx
	end
	if w < 1 or w > 64 then
		return nil
	end
	local bodyVal = style == "black" and 1 or 255
	local grid = {}
	for r = 1, h + 1 do -- one extra row so ink on the canvas bottom keeps its shadow
		local row = {}
		for c = 1, w do
			row[c] = 0
		end
		grid[r] = row
	end
	local top = obj.base - (by + bh) -- 0-based canvas row of the glyph's top
	-- some fonts declare a baseline their glyphs contradict (e.g. FBB yoff 0 /
	-- FONT_ASCENT = height, yet glyphs descend with negative by): a glyph that
	-- would overflow the bottom is shifted up to fit instead of getting clipped
	if top + bh > h then
		top = h - bh
	end
	if top < 0 then
		top = 0 -- taller than the canvas: keep the top rows, clip the rest
	end
	local r = 0
	for line in chunk:sub(bitmapPos + 6):gmatch("%x+") do
		if r >= bh then
			break
		end
		local rowY = top + r + 1
		if rowY >= 1 and rowY <= h then
			local row = grid[rowY]
			local ci = 0
			for hx in line:gmatch("%x") do
				local v = tonumber(hx, 16)
				for bit = 3, 0, -1 do
					if floor(v / 2 ^ bit) % 2 == 1 then
						local x = bx + ci * 4 + (3 - bit) + 1
						if x >= 1 and x <= w then
							row[x] = bodyVal
						end
					end
				end
				ci = ci + 1
			end
		end
		r = r + 1
	end
	if style == "shadow" then -- drop shadow: body offset by (+1,+1), value 1
		for rr = h, 1, -1 do
			local row = grid[rr]
			local below = grid[rr + 1]
			for cc = w, 1, -1 do
				if row[cc] == 255 then
					if below and cc + 1 <= w and below[cc + 1] == 0 then
						below[cc + 1] = 1
					end
				end
			end
		end
	elseif style == "glow" then -- 4-neighbour outline, value 1 (Book/Book2)
		for rr = 1, h + 1 do
			local row = grid[rr]
			for cc = 1, w do
				if row[cc] == 255 then
					if cc > 1 and row[cc - 1] == 0 then
						row[cc - 1] = 1
					end
					if cc < w and row[cc + 1] == 0 then
						row[cc + 1] = 1
					end
					local up = grid[rr - 1]
					if up and up[cc] == 0 then
						up[cc] = 1
					end
					local dn = grid[rr + 1]
					if dn and dn[cc] == 0 then
						dn[cc] = 1
					end
				end
			end
		end
	end
	-- emit only the ink band: the blank rows the BDF pads its canvas with are
	-- cropped no matter what; shadow always keeps one extra row so the bottom
	-- ink row's drop shadow survives (the grid has h+1 rows for exactly this)
	local sliceTop, sliceBot = obj.bandTop, obj.bandBot
	if style == "shadow" then
		sliceBot = sliceBot + 1
	elseif style == "glow" then -- keep the outline above AND below the ink
		if sliceTop > 1 then
			sliceTop = sliceTop - 1
		end
		sliceBot = sliceBot + 1
	end
	local parts = {}
	for rr = sliceTop, sliceBot do
		parts[#parts + 1] = string.char(unpack(grid[rr]))
	end
	local bytes = table.concat(parts)
	local ptr = mem.StaticAlloc(#bytes)
	copy(ptr, bytes)
	return {glyph = ptr, w = w, a = 0, c = 0, h = sliceBot - sliceTop + 1, y = 0}
end

-- detect the host font's native glyph style by sampling its own glyph pixels
-- (same criterion as the offline font survey): only value-1 pixels = black
-- (e.g. Autonote), 255 with few/no 1s = plain (e.g. Spell), both = shadow
-- unless the 1s also flank the body's left side, which means a four-side
-- outline = glow (Book/Book2)
local function detectStyle(font)
	local m = getFontM(font)
	if m.style then
		return m.style
	end
	local n255, n1, nGlowSide = 0, 0, 0
	local lastInk = -1 -- deepest row with any pixel (fallback bottom measure)
	local botFreq = {} -- per-char bottom rows of 0-9/A-Z: most of them sit
	local scanned = 0  -- flat on the baseline, so the MODE is the baseline
	local c = m.min    -- (a max would get dragged down by Q/J-style tails)
	while c <= m.max and scanned < 16384 do
		local t = getABC(m, font, c)
		local w = t[2]
		if w > 0 and w <= 64 then
			local isBase = (c >= 0x30 and c <= 0x39) or (c >= 0x41 and c <= 0x5A)
			local g = fntGlyph(font, c)
			local nb = w * m.h
			local charBot = -1
			for i = 0, nb - 1 do
				local v = u1[g + i]
				if v ~= 0 then
					local r = floor(i / w)
					if r > lastInk then
						lastInk = r
					end
					if r > charBot then
						charBot = r
					end
					if v == 255 then
						n255 = n255 + 1
					elseif v == 1 then
						n1 = n1 + 1
						-- a value-1 pixel with body to its RIGHT sits on the
						-- body's left flank: drop shadows (+1,+1) almost
						-- never do that, glow outlines always do
						if i % w + 1 < w and u1[g + i + 1] == 255 then
							nGlowSide = nGlowSide + 1
						end
					end
				end
			end
			if isBase and charBot >= 0 then
				botFreq[charBot] = (botFreq[charBot] or 0) + 1
			end
			scanned = scanned + nb
		end
		c = c + 1
	end
	local baseRow, baseN = -1, 0
	for row, cnt in pairs(botFreq) do
		if cnt > baseN or (cnt == baseN and row > baseRow) then
			baseRow, baseN = row, cnt
		end
	end
	local style
	if n255 == 0 and n1 > 0 then
		style = "black"
	elseif n255 > 0 and n1 <= n255 * 0.15 then
		style = "plain"
	elseif nGlowSide >= n1 * 0.2 then
		style = "glow" -- symmetric outline (Book/Book2 do this)
	else
		style = "shadow"
	end
	m.style = style
	m.botGap = lastInk >= 0 and (m.h - 1 - lastInk) or 0
	m.baseRow = baseRow >= 0 and baseRow or nil
	dlog(format("font %X style detected: %s (255:%d 1:%d glowside:%d), bottom pad %d, baseline %s",
		font, style, n255, n1, nGlowSide, m.botGap, tostring(m.baseRow)))
	return style
end

-- per-font extra line spacing (the ",N" ini flag): the engines advance text
-- lines by fontHeight-3, reading the height byte from the font object - so
-- bump this font's height by N and repoint its glyphs at copies padded with
-- N blank bottom rows; layout, height measurement and SBCS drawing all
-- follow for THIS font only. The glyph offsets at +0xC20 are u32s the engine
-- adds to font+0x1020, so pointing them into our own memory is plain
-- wrap-around arithmetic. If the engine ever reloads the font the edits
-- revert as one (safe); the height guard re-applies them on the next use.
local hostPadded = {}
local function padHostFont(font, n)
	if hostPadded[font] == fntHeight(font) then
		return
	end
	local h = fntHeight(font)
	local ws, total = {}, 0
	for c = 0, 255 do
		local _, w = fntABC(font, c)
		if w < 1 or w > 64 then
			w = 0
		end
		ws[c] = w
		total = total + w * (h + n)
	end
	local blob = mem.StaticAlloc(total)
	local pos = blob
	for c = 0, 255 do
		local w = ws[c]
		if w > 0 then
			copy(pos, fntGlyph(font, c), w * h)
			for i = 0, w * n - 1 do
				u1[pos + w * h + i] = 0
			end
			i4[font + 0xC20 + 4 * c] = pos - (font + 0x1020)
			pos = pos + w * (h + n)
		end
	end
	u1[font + 5] = h + n
	hostPadded[font] = h + n
	dlog(format("font %X per-font line spacing +%d: height %d -> %d, glyphs relocated",
		font, n, h, h + n))
end

-- which BDF (if any) an engine font uses; false = use the legacy page fonts
local bdfFor = {}
local function bdfForFont(font)
	local v = bdfFor[font]
	if v ~= nil then
		return v or nil
	end
	local spec
	for _, nm in ipairs(FONTNAMES) do
		local ok, f = pcall(function()
			return Game[nm .. "_fnt"]
		end)
		if ok and f == font then
			spec = bdfMap[nm]
			break
		end
	end
	local file, style, adj
	if spec then
		file, style, adj = spec.file, spec.style, spec.adj
	elseif bdfMap.Default then
		-- pick from the Default list by height: largest BDF that fits the
		-- font, else the smallest available (page-font heuristic)
		local d = bdfMap.Default
		style = d.style
		adj = d.adj
		local fh = fntHeight(font)
		local bestFile, bestH, minFile, minH
		for _, cand in ipairs(d.files) do
			local h = bdfHeight(cand)
			if h then
				if h <= fh and (not bestH or h > bestH) then
					bestFile, bestH = cand, h
				end
				if not minH or h < minH then
					minFile, minH = cand, h
				end
			end
		end
		file = bestFile or minFile
	end
	local obj = file and loadBdf(file)
	if obj then
		local pad = adj or 0
		if pad < 0 then
			pad = 0
		elseif pad > 10 then
			pad = 10
		end
		if pad > 0 then
			padHostFont(font, pad)
		end
		local det = detectStyle(font) -- also measures baseline/bottom padding
		-- auto gap: put the CJK glyph's bottom one row below the host font's
		-- baseline (Latin text's visual bottom), so mixed lines align; fall
		-- back to the host's deepest-ink padding if no baseline was sampled
		local m = getFontM(font)
		local autoGap = m.baseRow and (m.h - 2 - m.baseRow) or m.botGap or 0
		if autoGap < 0 then
			autoGap = 0
		end
		v = {obj = obj, style = style or det, gap = autoGap, pad = pad}
		dlog(format("font %X h=%d -> BDF %s (%s, gap %d%s)", font, fntHeight(font),
			file, v.style, v.gap, pad > 0 and format(", pad +%d", pad) or ""))
	else
		v = false
	end
	bdfFor[font] = v
	return v or nil
end

-- per (SBCS font, CJK char) glyph record cache; false = not renderable
local cjkCache = {}
local function getCJK(font, hi, lo)
	local fc = cjkCache[font]
	if not fc then
		fc = {}
		cjkCache[font] = fc
	end
	local key = hi * 256 + lo
	local rec = fc[key]
	if rec == false then
		return false
	end
	if rec then
		if rec.pi == nil or pageAlive(rec.pi) then
			return rec -- BDF-backed records (pi == nil) live in our own memory
		end
		fc[key] = nil -- stale record (page evicted); rebuild below, others self-heal on use
	end
	local bf = bdfForFont(font)
	if bf then
		local cp = toUnicode(hi, lo)
		rec = cp and bdfBuildGlyph(bf.obj, cp, bf.style) or false
		if rec then
			-- bottom-anchored: exactly bf.gap blank rows stay under the glyph
			local yOff = fntHeight(font) - bf.gap - rec.h
			rec.y = yOff > 0 and yOff or 0
		end
		fc[key] = rec
		return rec
	end
	local pi = getPage(getReplInfo(font).tag, hi)
	if not pi then
		return false -- not cached: the page may load fine on a later attempt
	end
	local page = pi.addr
	local a, w, sa = fntABC(page, lo)
	local ph = pi.h
	if w <= 0 or w > 64 then
		rec = false -- this glyph really has no valid shape: cache the verdict
	else
		local yOff = floor((fntHeight(font) - ph) / 2)
		if yOff < 0 then
			yOff = 0 -- page taller than the font: never draw above the pen
		end
		rec = {glyph = fntGlyph(page, lo), w = w, a = a, c = sa, h = ph, y = yOff, pi = pi}
	end
	fc[key] = rec
	return rec
end

-- ============ LEGACY MARKER TEXT BRIDGE ============
-- old preprocessed format: [SO][SP][SO] hi lo [BEL] ... [SI]; decode on sight
-- so old savegames / not-yet-converted data files keep displaying correctly

local function decodeSpecial(s)
	s = s:gsub("\32\14(..)\7", "%1")
	s = s:gsub("\14([^\15]*)\15", "%1")
	s = s:gsub("[\14\15]", "")
	return s
end

-- ============ KINSOKU (codes are hiByte*256+loByte in the game encoding) ============

local noStart, noEnd = {}, {}
if globalEncoding == "gb2312" or globalEncoding == "gbk" then
	for _, c in ipairs({ -- must not start a line: 。，、；：？！…—～·”’）》」』〕〗】．
		0xA1A3, 0xA3AC, 0xA1A2, 0xA3BB, 0xA3BA, 0xA3BF, 0xA3A1, 0xA1AD, 0xA1AA, 0xA1AB,
		0xA1A4, 0xA1B1, 0xA1AF, 0xA3A9, 0xA1B7, 0xA1B9, 0xA1BB, 0xA1B3, 0xA1BD, 0xA1BF, 0xA3AE}) do
		noStart[c] = true
	end
	for _, c in ipairs({ -- must not end a line: “‘（《「『〔〖【
		0xA1B0, 0xA1AE, 0xA3A8, 0xA1B6, 0xA1B8, 0xA1BA, 0xA1B2, 0xA1BC, 0xA1BE}) do
		noEnd[c] = true
	end
elseif globalEncoding == "big5" then
	for _, c in ipairs({ -- must not start a line: 。，、；：？！…—～‧·”’）》〉」』〕】．｝
		0xA143, 0xA141, 0xA142, 0xA146, 0xA147, 0xA148, 0xA149, 0xA14B, 0xA158, 0xA1E3,
		0xA145, 0xA150, 0xA1A8, 0xA1A6, 0xA15E, 0xA16E, 0xA172, 0xA176, 0xA17A, 0xA166,
		0xA16A, 0xA144, 0xA162}) do
		noStart[c] = true
	end
	for _, c in ipairs({ -- must not end a line: “‘（《〈「『〔【｛
		0xA1A7, 0xA1A5, 0xA15D, 0xA16D, 0xA171, 0xA175, 0xA179, 0xA165, 0xA169, 0xA161}) do
		noEnd[c] = true
	end
elseif globalEncoding == "shift_jis" then
	for _, c in ipairs({ -- must not start a line: 。、，．・：；？！゛゜ー…‥々ゝゞヽヾ）〕］｝〉》」』】
		0x8142, 0x8141, 0x8143, 0x8144, 0x8145, 0x8146, 0x8147, 0x8148, 0x8149, 0x814A,
		0x814B, 0x815B, 0x8163, 0x8164, 0x8158, 0x8154, 0x8155, 0x8152, 0x8153, 0x816A,
		0x816C, 0x816E, 0x8170, 0x8172, 0x8174, 0x8176, 0x8178, 0x817A,
		-- and small kana: ぁぃぅぇぉっゃゅょゎ ァィゥェォッャュョヮヵヶ
		0x829F, 0x82A1, 0x82A3, 0x82A5, 0x82A7, 0x82C1, 0x82E1, 0x82E3, 0x82E5, 0x82EC,
		0x8340, 0x8342, 0x8344, 0x8346, 0x8348, 0x8362, 0x8383, 0x8385, 0x8387, 0x838E,
		0x8395, 0x8396}) do
		noStart[c] = true
	end
	for _, c in ipairs({ -- must not end a line: （〔［｛〈《「『【
		0x8169, 0x816B, 0x816D, 0x816F, 0x8171, 0x8173, 0x8175, 0x8177, 0x8179}) do
		noEnd[c] = true
	end
end

-- ============ MEASURING (patch B core) ============
-- mirrors engine GetLineWidth: stops at \t \n \r, skips \f+5 digits,
-- spaceBefore skipped for the first byte, spaceAfter always added

local function measureLine(s, font)
	local m = getFontM(font)
	local w = 0
	local i, n = 1, #s
	while i <= n do
		local c = byte(s, i)
		if c >= leadMin and validHi(c) and i < n and validLo(byte(s, i + 1)) then
			local rec = getCJK(font, c, byte(s, i + 1))
			if rec then
				w = w + (i > 1 and rec.a or 0) + rec.w + rec.c
			end
			i = i + 2
		elseif c == 9 or c == 10 or c == 13 then
			break
		elseif c == 12 then
			i = i + 6
		elseif c < leadMin and c >= m.min and c <= m.max then
			local t = getABC(m, font, c)
			w = w + (i > 1 and t[1] or 0) + t[2] + t[3]
			i = i + 1
		else
			i = i + 1
		end
	end
	return w
end

-- ============ WORD WRAP (patches C / C' core) ============

-- tokenize into CJK chars / ASCII words / spaces / control codes, with advance widths.
-- font2 ~= nil enables WordWrap2 semantics: '_' switches to font2 until '\n'
local function tokenize(s, font1, font2)
	local toks = {}
	local font = font1
	local m = getFontM(font)
	local i, n = 1, #s
	while i <= n do
		local c = byte(s, i)
		if c >= leadMin and validHi(c) and i < n and validLo(byte(s, i + 1)) then
			local lo = byte(s, i + 1)
			local rec = getCJK(font, c, lo)
			toks[#toks + 1] = {s = s:sub(i, i + 1), k = "cjk", code = c * 256 + lo,
				w = rec and (rec.a + rec.w + rec.c) or fntHeight(font), f2 = font == font2}
			i = i + 2
		elseif c == 10 then
			toks[#toks + 1] = {s = "\n", w = 0, k = "nl"}
			font = font1
			m = getFontM(font)
			i = i + 1
		elseif c == 9 then
			toks[#toks + 1] = {s = s:sub(i, i + 3), w = 0, k = "tab",
				v = tonumber(s:sub(i + 1, i + 3)) or 0}
			i = i + 4
		elseif c == 12 then
			toks[#toks + 1] = {s = s:sub(i, i + 5), w = 0, k = "ctl"}
			i = i + 6
		elseif c == 13 then -- only reached with keepR ~= 0: engine skips the byte
			toks[#toks + 1] = {s = "\13", w = 0, k = "ctl"}
			i = i + 1
		elseif c == 32 then
			toks[#toks + 1] = {s = " ", w = getABC(m, font, 32)[2], k = "sp", f2 = font == font2}
			i = i + 1
		elseif font2 and c == 0x5F then -- '_' switches to font2 (scroll headers)
			font = font2
			m = getFontM(font)
			toks[#toks + 1] = {s = "_", w = 0, k = "fsw", f2 = true}
			i = i + 1
		else -- ASCII word: maximal unbreakable run
			local j, w = i, 0
			while j <= n do
				local cj = byte(s, j)
				if cj >= leadMin or cj == 32 or cj < 14 or (font2 and cj == 0x5F) then
					break
				end
				if cj >= m.min and cj <= m.max then
					local t = getABC(m, font, cj)
					w = w + t[1] + t[2] + t[3]
				end
				j = j + 1
			end
			if j == i then
				j = i + 1 -- lone unprintable byte: copy through, zero width
			end
			toks[#toks + 1] = {s = s:sub(i, j - 1), w = w, k = "word", f2 = font == font2}
			i = j
		end
	end
	return toks
end

local wrapCache = setmetatable({}, {__mode = "v"})

local function wrapText(s, font1, font2, W, x0)
	local ck = s .. "\1" .. font1 .. "\1" .. (font2 or 0) .. "\1" .. W .. "\1" .. x0
	local hit = wrapCache[ck]
	if hit then
		return hit
	end
	local toks = tokenize(s, font1, font2)
	local res = {}
	local resetX = x0
	local lineW = x0
	local lineStart = 1 -- first res index belonging to the current line

	local function breakableAfter(j)
		local t = res[j]
		local nx = res[j + 1]
		if t.k == "sp" then
			return true
		end
		if t.k == "cjk" and not noEnd[t.code] then
			if nx and nx.k == "cjk" and noStart[nx.code] then
				return false
			end
			return true
		end
		if t.k == "word" and nx and nx.k == "cjk" and not noStart[nx.code] then
			return true
		end
		return false
	end

	local function doBreak(j, tf2)
		-- font2 flag of whatever starts the next line: the token after the break
		-- point, or the incoming token when breaking at the end of the line
		local f2next = (j < #res) and res[j + 1].f2 or tf2
		local nl = (font2 and f2next) and "\n_" or "\n"
		if res[j].k == "sp" then -- engine semantics: the space becomes the line break
			res[j] = {s = nl, w = 0, k = "nl"}
			lineStart = j + 1
		else
			table.insert(res, j + 1, {s = nl, w = 0, k = "nl"})
			lineStart = j + 2
		end
		local w = resetX
		for k = lineStart, #res do
			w = w + res[k].w
		end
		lineW = w
	end

	for ti = 1, #toks do
		local t = toks[ti]
		if t.k == "nl" then
			res[#res + 1] = t
			lineW = resetX
			lineStart = #res + 1
		elseif t.k == "tab" then -- \t### : pen jumps to absolute position, anchors \n resets
			res[#res + 1] = t
			lineW = x0 + t.v
			resetX = lineW
			lineStart = #res + 1
		elseif t.k == "ctl" or t.k == "fsw" then
			res[#res + 1] = t
		elseif t.k == "sp" then
			res[#res + 1] = t
			lineW = lineW + t.w
		else -- word / cjk
			if lineW + t.w >= W and #res >= lineStart
			and not (t.k == "cjk" and noStart[t.code]) then -- kinsoku: let punctuation hang
				local brk
				local j = #res
				while j >= lineStart do
					if breakableAfter(j) then
						brk = j
						break
					end
					j = j - 1
				end
				if brk then
					doBreak(brk, t.f2)
				else -- no legal break point on this line: hard break before the token
					res[#res + 1] = {s = (font2 and t.f2) and "\n_" or "\n", w = 0, k = "nl"}
					lineW = resetX
					lineStart = #res + 1
				end
			end
			res[#res + 1] = t
			lineW = lineW + t.w
		end
	end

	local parts, total = {}, 0
	for k = 1, #res do
		local b = res[k].s
		if total + #b > WRAP_CAP then
			break
		end
		parts[#parts + 1] = b
		total = total + #b
	end
	local out = table.concat(parts)
	wrapCache[ck] = out
	return out
end

-- ============ HANDLER CORES (return nil => fall back to original engine code) ============

local function widthHandler(font, str)
	if str == 0 then
		return nil
	end
	local s = memstr(str)
	local decoded = false
	if s:find("\14", 1, true) then
		s = decodeSpecial(s)
		decoded = true
	end
	if not decoded and not s:find("[\129-\255]") then
		return nil -- pure ASCII: original engine path
	end
	dlogOnce("fire:B", "B first fire (" .. #s .. " bytes)")
	return measureLine(s, font)
end

local traceLeft = 80
local function trace(msg)
	if traceLeft > 0 then
		traceLeft = traceLeft - 1
		dlog(msg)
	end
end

local function wrapHandler(str, font1, font2, dlg, x, keepR)
	if str == 0 then
		u1[ADDR.WrapBuf] = 0
		return ADDR.WrapBuf
	end
	local s = memstr(str)
	local decoded = false
	if s:find("\14", 1, true) then
		s = decodeSpecial(s)
		decoded = true
	end
	if not decoded and not s:find("[\129-\255]") then
		return nil -- pure ASCII: original engine path
	end
	if keepR == 0 and s:find("\13", 1, true) then
		return str -- engine semantics: \r means "do not wrap", return input as-is
	end
	dlogOnce(font2 and "fire:C2" or "fire:C",
		(font2 and "wrap2" or "wrap") .. " first fire (" .. #s .. " bytes)")
	trace(format("%s len=%d f1=%X f2=%X W=%d x=%d",
		font2 and "wrap2" or "wrap", #s, font1, font2 or 0, i4[dlg + 8], x))
	local out = wrapText(s, font1, font2, i4[dlg + 8], x)
	copy(ADDR.WrapBuf, out .. "\0")
	trace("  -> " .. #out .. " bytes")
	return ADDR.WrapBuf
end

-- shared pair fetch/validation; returns hi, lo (or nil if not a renderable pair)
local function fetchPair(hiByte, strPtr, idx, len)
	if idx + 1 >= len then
		return
	end
	local lo = u1[strPtr + idx + 1]
	if validHi(hiByte) and validLo(lo) then
		return hiByte, lo
	end
end

-- ============ LOOP HANDLERS (patches D/E/F/G) ============

-- D: main DrawText loop. Locals (identical in MM7/MM8): [ebp-4] text,
-- [ebp+0x14] index, [ebp-0xC] len, ebx font, esi penX, edi penY,
-- [ebp+0x10] color, [ebp+0x20] shadow
local function handlerD(d, ch)
	local ebp = d.ebp
	local idx = i4[ebp + 0x14]
	dlogOnce("fire:D", format("D first hit: idx=%d len=%d str=%X ch=%02X",
		idx, i4[ebp - 0xC], i4[ebp - 4], ch))
	local hi, lo = fetchPair(ch, i4[ebp - 4], idx, i4[ebp - 0xC])
	if not hi then
		return
	end
	local font = d.ebx
	i4[ebp + 0x14] = idx + 1
	local rec = getCJK(font, hi, lo)
	if not rec then
		d.esi = d.esi + fntHeight(font)
		return
	end
	local x = d.esi + (idx > 0 and rec.a or 0)
	local color = u2[ebp + 0x10]
	if color ~= 0 then
		call(ADDR.BlitGlyphShadow, 1, ADDR.Screen, x, d.edi + rec.y, rec.glyph,
			rec.w, rec.h, i4[font + 0xC], color, u2[ebp + 0x20])
	else
		call(ADDR.BlitGlyph, 1, ADDR.Screen, x, d.edi + rec.y, rec.glyph,
			rec.w, rec.h, i4[font + 0xC], i4[ebp + 0x18])
	end
	d.esi = x + rec.w + rec.c
end

-- E1: DrawTextLimited truncation-measure loop (buf 0x5E1020). Locals:
-- [ebp+0x14] index, [ebp-4] len, edi font, esi accumulated width
local function handlerE1(d, ch)
	local ebp = d.ebp
	local idx = i4[ebp + 0x14]
	dlogOnce("fire:E1", format("E1 first hit: idx=%d len=%d ch=%02X", idx, i4[ebp - 4], ch))
	local hi, lo = fetchPair(ch, ADDR.LtdBuf, idx, i4[ebp - 4])
	if not hi then
		return
	end
	local font = d.edi
	i4[ebp + 0x14] = idx + 1
	local rec = getCJK(font, hi, lo)
	if rec then
		d.esi = d.esi + (idx > 0 and rec.a or 0) + rec.w + rec.c
	else
		d.esi = d.esi + fntHeight(font)
	end
end

-- E2: DrawTextLimited inline draw loop. Locals: [ebp+0x14] index into 0x5E1020,
-- [ebp+0x18] parallel text pointer, [ebp-4] len, edi font, esi penX, ebx penY,
-- [ebp+0x10] color; char is in eax/al (cl is clobbered by the dispatch)
local function handlerE2(d, ch)
	local ebp = d.ebp
	local idx = i4[ebp + 0x14]
	dlogOnce("fire:E2", format("E2 first hit: idx=%d len=%d ch=%02X", idx, i4[ebp - 4], ch))
	local hi, lo = fetchPair(ch, ADDR.LtdBuf, idx, i4[ebp - 4])
	if not hi then
		return
	end
	local font = d.edi
	i4[ebp + 0x14] = idx + 1
	i4[ebp + 0x18] = i4[ebp + 0x18] + 1
	local rec = getCJK(font, hi, lo)
	if not rec then
		d.esi = d.esi + fntHeight(font)
		return
	end
	local x = d.esi + (idx > 0 and rec.a or 0)
	local color = u2[ebp + 0x10]
	if color ~= 0 then
		call(ADDR.BlitGlyphShadow, 1, ADDR.Screen, x, d.ebx + rec.y, rec.glyph,
			rec.w, rec.h, i4[font + 0xC], color, 0)
	else
		call(ADDR.BlitGlyph, 1, ADDR.Screen, x, d.ebx + rec.y, rec.glyph,
			rec.w, rec.h, i4[font + 0xC], 0)
	end
	d.esi = x + rec.w + rec.c
end

-- F: scroll line renderer into 16bpp buffer (0x44A7B2). Locals: [ebp-4] index,
-- [ebp+0x10] text, [ebp-0xC] len, esi font, edi dest pixel ptr, [ebp-8] color,
-- [ebp+0x14] pitch; char in eax/al
local function handlerF(d, ch)
	local ebp = d.ebp
	local idx = i4[ebp - 4]
	dlogOnce("fire:F", format("F first hit: idx=%d len=%d str=%X ch=%02X pitch=%d",
		idx, i4[ebp - 0xC], i4[ebp + 0x10], ch, i4[ebp + 0x14]))
	local hi, lo = fetchPair(ch, i4[ebp + 0x10], idx, i4[ebp - 0xC])
	if not hi then
		return
	end
	local font = d.esi
	i4[ebp - 4] = idx + 1
	local rec = getCJK(font, hi, lo)
	if not rec then
		d.edi = d.edi + fntHeight(font) * 2
		return
	end
	local color = i4[ebp - 8]
	if color == 0 then
		color = 0xFFFF
	end
	local pitch2 = i4[ebp + 0x14] * 2
	local dest = d.edi + (idx > 0 and rec.a or 0) * 2
	call(ADDR.BlitGlyphToBuf, 2, dest + rec.y * pitch2, rec.glyph,
		rec.w, rec.h, i4[font + 0xC], color, pitch2)
	d.edi = dest + (rec.w + rec.c) * 2
end

-- G: centered-text line renderer (0x44A8E5). Locals: ebx index, [ebp+0x10] text,
-- [ebp-8] len, esi font, edi penX, [ebp+0xC] penY, [ebp-4] color; char in eax/al
local function handlerG(d, ch)
	local ebp = d.ebp
	local idx = d.ebx
	dlogOnce("fire:G", format("G first hit: idx=%d len=%d str=%X ch=%02X",
		idx, i4[ebp - 8], i4[ebp + 0x10], ch))
	local hi, lo = fetchPair(ch, i4[ebp + 0x10], idx, i4[ebp - 8])
	if not hi then
		return
	end
	local font = d.esi
	d.ebx = idx + 1
	local rec = getCJK(font, hi, lo)
	if not rec then
		d.edi = d.edi + fntHeight(font)
		return
	end
	local color = i4[ebp - 4]
	if color == 0 then
		color = 0xFFFF
	end
	local x = d.edi + (idx > 0 and rec.a or 0)
	call(ADDR.BlitGlyphShadow, 1, ADDR.Screen, x, i4[ebp + 0xC] + rec.y, rec.glyph,
		rec.w, rec.h, i4[font + 0xC], color, 0)
	d.edi = x + rec.w + rec.c
end

-- ============ MM6 LOOP HANDLERS ============
-- MM6 frames are esp-relative. Inside a mem.hook the reported esp points at the
-- hook call's return address, so the hooked context's esp is d.esp + 4.
-- The pen is a pointer into the 16bpp framebuffer; pitch comes from the
-- scanline table. Blitters: fastcall(destPixels, glyph; w, h, pal[, color...]).

-- debug: on the first blit of each (font, char), dump the glyph record and a
-- per-row nonzero-byte count of the glyph memory as the blitter will read it
local blitLogged = {}
local function dlogBlit(tag, font, hi, lo, rec)
	if not logEnabled then
		return
	end
	local key = format("%s%X_%04X", tag, font, hi * 256 + lo)
	if blitLogged[key] then
		return
	end
	blitLogged[key] = true
	local rows = {}
	for r = 0, rec.h - 1 do
		local n = 0
		local rbase = rec.glyph + r * rec.w
		for c = 0, rec.w - 1 do
			if u1[rbase + c] ~= 0 then
				n = n + 1
			end
		end
		rows[#rows + 1] = n
	end
	dlog(format("%s f=%X fh=%d ch=%02X%02X w=%d h=%d y=%d g=%X ink=%s",
		tag, font, fntHeight(font), hi, lo, rec.w, rec.h, rec.y, rec.glyph,
		table.concat(rows, ",")))
end

local function screenPitch2()
	return (i4[ADDR.RowTable + 4] - i4[ADDR.RowTable]) * 2
end

local function blit6Screen(dest, rec, font, color)
	if color ~= 0 then
		call(ADDR.BlitColored, 2, dest + rec.y * screenPitch2(), rec.glyph,
			rec.w, rec.h, i4[font + 0xC], color)
	else
		call(ADDR.BlitPlain, 2, dest + rec.y * screenPitch2(), rec.glyph,
			rec.w, rec.h, i4[font + 0xC])
	end
end

-- D (MM6 Draw loop): [esp+0x48] char ptr, edi index, [esp+0x10] len,
-- ebp font, esi dest pixel ptr, [esp+0x44] color word
local function handlerD6(d, ch)
	local esp = d.esp + 4
	local idx = d.edi
	local len = i4[esp + 0x10]
	dlogOnce("fire:D", format("D6 first hit: idx=%d len=%d ch=%02X", idx, len, ch))
	if idx + 1 >= len then
		return
	end
	local charPtr = i4[esp + 0x48]
	local lo = u1[charPtr + 1]
	if not (validHi(ch) and validLo(lo)) then
		return
	end
	local font = d.ebp
	i4[esp + 0x48] = charPtr + 1
	d.edi = idx + 1
	local rec = getCJK(font, ch, lo)
	if not rec then
		d.esi = d.esi + fntHeight(font) * 2
		return
	end
	local dest = d.esi + (idx > 0 and rec.a * 2 or 0)
	dlogBlit("D6", font, ch, lo, rec)
	blit6Screen(dest, rec, font, u2[esp + 0x44])
	d.esi = dest + (rec.w + rec.c) * 2
end

-- E1 (MM6 truncate loop): edx index, ebx len, ebp font, ecx accumulated width
local function handlerE16(d, ch)
	local idx = d.edx
	local len = d.ebx
	dlogOnce("fire:E1", format("E1/6 first hit: idx=%d len=%d ch=%02X", idx, len, ch))
	if idx + 1 >= len then
		return
	end
	local lo = u1[ADDR.LtdBuf + idx + 1]
	if not (validHi(ch) and validLo(lo)) then
		return
	end
	local font = d.ebp
	d.edx = idx + 1
	local rec = getCJK(font, ch, lo)
	if rec then
		d.ecx = d.ecx + (idx > 0 and rec.a or 0) + rec.w + rec.c
	else
		d.ecx = d.ecx + fntHeight(font)
	end
end

-- E2 (MM6 limited draw loop): ebx char ptr, edi parallel digit ptr,
-- [esp+0x40] index, [esp+0x3C] len, ebp font, esi dest ptr, [esp+0x38] color
local function handlerE26(d, ch)
	local esp = d.esp + 4
	local idx = i4[esp + 0x40]
	local len = i4[esp + 0x3C]
	dlogOnce("fire:E2", format("E2/6 first hit: idx=%d len=%d ch=%02X", idx, len, ch))
	if idx + 1 >= len then
		return
	end
	local charPtr = d.ebx
	local lo = u1[charPtr + 1]
	if not (validHi(ch) and validLo(lo)) then
		return
	end
	local font = d.ebp
	i4[esp + 0x40] = idx + 1
	d.ebx = charPtr + 1
	d.edi = d.edi + 1
	local rec = getCJK(font, ch, lo)
	if not rec then
		d.esi = d.esi + fntHeight(font) * 2
		return
	end
	local dest = d.esi + (idx > 0 and rec.a * 2 or 0)
	dlogBlit("E2", font, ch, lo, rec)
	blit6Screen(dest, rec, font, u2[esp + 0x38])
	d.esi = dest + (rec.w + rec.c) * 2
end

-- G (MM6 line-to-buffer renderer, used by DrawCentered and scrolls):
-- ebp index, [esp+0x34] text, [esp+0x14] len, esi font, edi dest ptr,
-- [esp+0x10] color (0 -> 0xFFFF), [esp+0x38] pitch
local function handlerG6(d, ch)
	local esp = d.esp + 4
	local idx = d.ebp
	local len = i4[esp + 0x14]
	dlogOnce("fire:G", format("G6 first hit: idx=%d len=%d ch=%02X", idx, len, ch))
	if idx + 1 >= len then
		return
	end
	local strPtr = i4[esp + 0x34]
	local lo = u1[strPtr + idx + 1]
	if not (validHi(ch) and validLo(lo)) then
		return
	end
	local font = d.esi
	d.ebp = idx + 1
	local rec = getCJK(font, ch, lo)
	if not rec then
		d.edi = d.edi + fntHeight(font) * 2
		return
	end
	local color = i4[esp + 0x10]
	if color == 0 then
		color = 0xFFFF
	end
	local pitch2 = i4[esp + 0x38] * 2
	local dest = d.edi + (idx > 0 and rec.a * 2 or 0)
	dlogBlit("G6", font, ch, lo, rec)
	dlogOnce("G6pitch" .. pitch2, format("G6 pitch2=%d", pitch2))
	call(ADDR.BlitToBuf, 2, dest + rec.y * pitch2, rec.glyph,
		rec.w, rec.h, i4[font + 0xC], color, pitch2)
	d.edi = dest + (rec.w + rec.c) * 2
end

-- ============ INSTALLATION ============
-- every step is pcall'd and logged; patch A goes last and only on full success

local installFailed = false
local function step(name, fn)
	local ok, err = pcall(fn)
	if ok then
		dlog("install " .. name .. ": ok")
	else
		installFailed = true
		dlog("install " .. name .. ": FAILED: " .. tostring(err))
	end
end

local function guarded(name, fn)
	return function(d)
		local ok, err = pcall(fn, d)
		if not ok then
			dlogOnce("err:" .. name, "ERROR in " .. name .. ": " .. tostring(err))
		end
	end
end

step("B GetLineWidth", function()
	mem.hookfunction(ADDR.GetLineWidth, 2, 0, function(d, def, font, str)
		local ok, r = pcall(widthHandler, font, str)
		if not ok then
			dlogOnce("err:B", "ERROR in B: " .. tostring(r))
			r = nil
		end
		return r or def(font, str)
	end)
end)

step("C WordWrap", function()
	if mmver == 6 then -- MM6 wrap has no keepR argument (\r always bails)
		mem.hookfunction(ADDR.WordWrap, 2, 2, function(d, def, str, font, dlg, x)
			local ok, r = pcall(wrapHandler, str, font, nil, dlg, x, 0)
			if not ok then
				dlogOnce("err:C", "ERROR in C: " .. tostring(r))
				r = nil
			end
			return r or def(str, font, dlg, x)
		end)
	else
		mem.hookfunction(ADDR.WordWrap, 2, 3, function(d, def, str, font, dlg, x, keepR)
			local ok, r = pcall(wrapHandler, str, font, nil, dlg, x, keepR)
			if not ok then
				dlogOnce("err:C", "ERROR in C: " .. tostring(r))
				r = nil
			end
			return r or def(str, font, dlg, x, keepR)
		end)
	end
end)

if ADDR.WordWrap2 then
	step("C' WordWrap2", function()
		mem.hookfunction(ADDR.WordWrap2, 2, 4, function(d, def, str, font1, font2, dlg, x, keepR)
			local ok, r = pcall(wrapHandler, str, font1, font2, dlg, x, keepR)
			if not ok then
				dlogOnce("err:C'", "ERROR in C': " .. tostring(r))
				r = nil
			end
			return r or def(str, font1, font2, dlg, x, keepR)
		end)
	end)
end

-- S: extra line spacing. The engines lay text out at fontHeight-3 px per
-- line (their own SBCS glyphs keep ~3 blank bottom rows, full-canvas CJK
-- glyphs don't - lines can touch). lineSpacing=N bumps every layout site
-- (drawing AND height measurement move together, so dialog boxes grow to
-- match) by patching the -3 immediates to -(3-N).
if lineSpacing > 0 then
	step("S lineSpacing +" .. lineSpacing, function()
		local function poke(a, orig, new)
			local cur = u1[a]
			if cur == orig then
				mem.asmpatch(a, format("db %d", new), 1)
			else
				dlog(format("S: skip %X (found %02X, expected %02X)", a, cur, orig))
			end
		end
		for _, a in ipairs(ADDR.LineLea) do
			poke(a, 0xFD, (0xFD + lineSpacing) % 256)
		end
		for _, a in ipairs(ADDR.LineSub) do
			-- imm8 is signed: sub reg, -N adds; mask to a byte for FASM
			poke(a, 0x03, (3 - lineSpacing) % 256)
		end
	end)
end

-- M: draw paths that bypass WordWrap (Draw with "bottom", DrawTextLimited's
-- truncation) would show legacy marker text raw - the markers are skipped as
-- invalid chars but their separator spaces render. Decode at the entries; the
-- decoded copy lives in our own static buffer, the input is never modified.
local drawScratch
local function bridgeStr(str)
	if str == 0 then
		return str
	end
	local s = memstr(str)
	if not s:find("\14", 1, true) then
		return str
	end
	s = decodeSpecial(s)
	if #s > WRAP_CAP then
		s = s:sub(1, WRAP_CAP)
	end
	copy(drawScratch, s .. "\0")
	return drawScratch
end

step("M1 DrawText bridge", function()
	drawScratch = drawScratch or mem.StaticAlloc(4096)
	if mmver == 6 then -- MM6 Draw has no opaque/bottom/shadow arguments
		mem.hookfunction(ADDR.Draw, 2, 4, function(d, def, dlg, font, x, y, color, str)
			local ok, s2 = pcall(bridgeStr, str)
			if not ok then
				dlogOnce("err:M1", "ERROR in M1: " .. tostring(s2))
				s2 = str
			end
			return def(dlg, font, x, y, color, s2)
		end)
	else
		mem.hookfunction(ADDR.Draw, 2, 7, function(d, def, dlg, font, x, y, color, str, opaque, bottom, shadow)
			local ok, s2 = pcall(bridgeStr, str)
			if not ok then
				dlogOnce("err:M1", "ERROR in M1: " .. tostring(s2))
				s2 = str
			end
			return def(dlg, font, x, y, color, s2, opaque, bottom, shadow)
		end)
	end
end)

step("M2 DrawTextLimited bridge", function()
	drawScratch = drawScratch or mem.StaticAlloc(4096)
	mem.hookfunction(ADDR.DrawTextLimited, 2, 6, function(d, def, dlg, font, x, y, color, str, w, right)
		local ok, s2 = pcall(bridgeStr, str)
		if not ok then
			dlogOnce("err:M2", "ERROR in M2: " .. tostring(s2))
			s2 = str
		end
		return def(dlg, font, x, y, color, s2, w, right)
	end)
end)

-- L: our wrap may change the text length, but GetTextHeight / GetTextHeight2 /
-- PageBreak take strlen of the *input* and Draw takes it before wrapping, then
-- all iterate over the wrapped buffer. Re-point them at the wrap result:
step("L1 GetTextHeight len", function()
	-- default: replace a "push <input str>" with "push eax" (the wrap result)
	mem.asmpatch(ADDR.L1[1], ADDR.L1[3] or "push eax", ADDR.L1[2])
end)
if ADDR.L2 then
	step("L2 GetTextHeight2 len", function()
		mem.asmpatch(ADDR.L2[1], "push eax", ADDR.L2[2])
	end)
end
if ADDR.L3 then
	step("L3 PageBreak len", function()
		mem.asmpatch(ADDR.L3[1], "push eax", ADDR.L3[2])
	end)
end
step("L4 DrawText len", function()
	-- recompute the draw loop's length local from the wrap result
	if mmver == 6 then
		-- at 0x44368D eax = wrap result, len lives at [esp+0x10]; MM6 has no
		-- strlen import here so inline scasb (edi = live x argument, preserved)
		mem.asmhook(ADDR.L4, [[
	push edi
	push eax
	mov edi, eax
	or ecx, -1
	xor eax, eax
	repne scasb
	not ecx
	dec ecx
	mov [esp+0x18], ecx
	pop eax
	pop edi
]])
	else
		mem.asmhook(ADDR.L4, [[
	push dword [ebp-4]
	call absolute ]] .. ADDR.Strlen .. [[

	pop ecx
	mov [ebp-0xC], eax
]])
	end
end)

-- each loop patch: at the printable-char branch, bytes >= leadMin divert to a
-- 5-nop stub carrying a Lua hook (draws the glyph, advances the pen, bumps the
-- loop index by 1 extra so the pair is consumed), then jump to loop-continue
local charGetters = {
	cl = function(d) return d.cl end,
	eax = function(d) return d.eax end,
	eaxlow = function(d) return d.eax % 0x100 end, -- al valid, upper bytes dirty
}

local function installLoopPatch(spec, name, handler)
	local getch = charGetters[spec.char]
	local hooked = guarded(name, function(d)
		return handler(d, getch(d))
	end)
	local proc = mem.asmproc("nop\nnop\nnop\nnop\nnop\njmp absolute " .. spec.cont)
	mem.hook(proc, hooked, 5)
	mem.asmpatch(spec.anchor,
		"cmp " .. spec.reg .. ", " .. leadMin .. "\njb @f\njmp absolute " .. proc .. "\n@@:\n" .. spec.orig,
		spec.size)
end

local loopHandlers
if mmver == 6 then
	loopHandlers = {D = handlerD6, E1 = handlerE16, E2 = handlerE26, G = handlerG6}
else
	loopHandlers = {D = handlerD, E1 = handlerE1, E2 = handlerE2, F = handlerF, G = handlerG}
end
for _, name in ipairs({"D", "E1", "E2", "F", "G"}) do
	if ADDR.loops[name] then
		step(name .. " loop", function()
			installLoopPatch(ADDR.loops[name], name, loopHandlers[name])
		end)
	end
end

if ADDR.TestChar then
if installFailed then
	dlog("A/A2 SKIPPED (an earlier step failed; DBCS stays off, game stays safe)")
else
	if ADDR.A2 then
		-- MM7: Draw's inlined validity test must accept lead bytes too
		step("A2 Draw inline test", function()
			local a2 = ADDR.A2
			mem.asmpatch(a2.anchor, [[
	cmp al, ]] .. leadMin .. [[

	jae absolute ]] .. a2.valid .. [[

	cmp al, [ebx]
	jb absolute ]] .. a2.invalid .. [[

	cmp al, [ebx+1]
]], a2.size)
		end)
	end
end
if installFailed then
	dlog("A TestChar: skipped unless all previous steps succeeded")
else
	step("A TestChar", function()
		local testCharProc = mem.asmproc([[
	cmp cl, ]] .. leadMin .. [[

	jae @f
	cmp cl, [edx]
	jb absolute ]] .. ADDR.TestCharInvalid .. [[

	cmp cl, [edx+1]
	jbe @f
	jmp absolute ]] .. ADDR.TestCharInvalid .. [[

@@:
	jmp absolute ]] .. ADDR.TestCharValid .. [[
]])
		mem.asmpatch(ADDR.TestChar, "jmp absolute " .. testCharProc, 9)
	end)
end
end -- ADDR.TestChar (MM6 has none: every loop diverts before its inline test)

dlog(installFailed and "install INCOMPLETE - native DBCS disabled" or "install complete")

-- ============ LEGACY SAVEGAME MIGRATION ============
-- old saves stored marker-encoded names/biographies; normalize them to plain text

function events.AfterLoadMap()
	local ok, err = pcall(function()
		local n = 0
		for i, pl in Party.PlayersArray do
			local nm = pl.Name
			if nm and nm:find("\14", 1, true) then
				pl.Name = decodeSpecial(nm)
				n = n + 1
			end
			local bio = pl.Biography
			if bio and bio:find("\14", 1, true) then
				pl.Biography = decodeSpecial(bio)
				n = n + 1
			end
		end
		if n > 0 then
			dlog("migrated " .. n .. " legacy marker name/bio fields")
		end
	end)
	if not ok then
		dlogOnce("err:migrate", "ERROR in migration: " .. tostring(err))
	end
end

-- ============ DEMO / PUBLIC API ============

DBCS = {
	decodeSpecial = decodeSpecial,
	measureLine = measureLine,
	wrapText = wrapText,
	getCJK = getCJK,
}

if nativeDemo and not installFailed then
	-- deferred to the first stable in-game frame: calling Message() from inside
	-- AfterLoadMap (mid map load) is not a safe engine state
	local demoText = "\212\173\201\250DBCS\178\226\202\212\163\186\196\227\186\195\163\172\202\192\189\231\163\161\213\226\210\187\182\206\202\199\205\234\200\171\195\187\211\208\212\164\188\211\185\164\177\234\188\199\181\196\180\191\206\196\177\190\163\172\211\195\192\180\209\233\214\164\215\212\182\175\187\187\208\208\202\199\183\241\187\225\212\218\200\206\210\226\186\186\215\214\214\174\186\243\183\162\201\250\163\172\210\212\188\176\208\208\202\215\189\251\212\242\163\168\182\186\186\197\161\162\190\228\186\197\178\187\179\246\207\214\212\218\208\208\202\215\163\169\181\196\180\166\192\237\161\163\161\182\196\167\183\168\195\197\161\183 Might and Magic \214\208\211\162\206\196\187\236\197\197 123 \178\226\202\212\161\163"
	local demoState = 0
	function events.Tick()
		if demoState == 2 then
			return
		end
		local ok, err = pcall(function()
			if demoState == 0 then
				if Game.CurrentScreen == 0 then
					demoState = 1 -- in game view; show on the next tick
					dlog("demo armed (game screen reached)")
				end
			else
				demoState = 2
				dlog("demo calling Message")
				Message(demoText)
				dlog("demo Message returned")
			end
		end)
		if not ok then
			demoState = 2
			dlogOnce("err:demo", "ERROR in demo: " .. tostring(err))
		end
	end
end
