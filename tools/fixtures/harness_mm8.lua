-- offline harness for FNT_DBCS.lua: fake mem/Game/events, fake fonts, drive hooks
unpack = unpack or table.unpack

-- ===== fake flat memory =====
local MEM = {}
local function rd(a, n)
	local v = 0
	for k = n - 1, 0, -1 do
		v = v * 256 + (MEM[a + k] or 0)
	end
	return v
end
local function wr(a, n, v)
	v = v % (2 ^ (8 * n))
	for k = 0, n - 1 do
		MEM[a + k] = v % 256
		v = math.floor(v / 256)
	end
end

CALLS, HOOKS, HF, PATCHES, ASMPROCS, ASMHOOKS = {}, {}, {}, {}, {}, {}

mem = {
	u1 = setmetatable({}, {__index = function(_, a) return MEM[a] or 0 end,
		__newindex = function(_, a, v) wr(a, 1, v) end}),
	u2 = setmetatable({}, {__index = function(_, a) return rd(a, 2) end,
		__newindex = function(_, a, v) wr(a, 2, v) end}),
	i4 = setmetatable({}, {__index = function(_, a)
			local v = rd(a, 4)
			if v >= 2 ^ 31 then v = v - 2 ^ 32 end
			return v
		end,
		__newindex = function(_, a, v) wr(a, 4, v) end}),
	string = function(p)
		local out, a = {}, p
		while (MEM[a] or 0) ~= 0 do
			out[#out + 1] = string.char(MEM[a])
			a = a + 1
		end
		return table.concat(out)
	end,
	copy = function(dest, s)
		for k = 1, #s do
			MEM[dest + k - 1] = s:byte(k)
		end
	end,
	call = function(...)
		CALLS[#CALLS + 1] = {...}
		return 0
	end,
	hook = function(p, f, size)
		HOOKS[p] = f
	end,
	asmproc = function(code)
		local p = 0x10000000 + #ASMPROCS * 0x100
		ASMPROCS[#ASMPROCS + 1] = {p = p, code = code}
		return p
	end,
	asmpatch = function(p, code, size)
		PATCHES[#PATCHES + 1] = {p = p, code = code, size = size}
	end,
	asmhook = function(p, code, size)
		ASMHOOKS[#ASMHOOKS + 1] = {p = p, code = code}
	end,
	hookfunction = function(p, nreg, nstack, f)
		HF[p] = {nreg = nreg, nstack = nstack, f = f}
	end,
	StaticAlloc = function(n)
		NEXTALLOC = (NEXTALLOC or 0x20000000) + 0x1000
		return NEXTALLOC
	end,
}

-- ===== fake fonts =====
local NEXTF = 0x01000000
local function makeFont(minC, maxC, h, defW, spaceW, sb, sa)
	local f = NEXTF
	NEXTF = NEXTF + 0x20000
	wr(f, 1, minC); wr(f + 1, 1, maxC); wr(f + 5, 1, h)
	wr(f + 0xC, 4, 0xAB0000 + h)
	for c = 0, 255 do
		local base = f + 0x20 + 12 * c
		wr(base, 4, sb)
		wr(base + 4, 4, (c == 32) and spaceW or defW)
		wr(base + 8, 4, sa)
		wr(f + 0xC20 + 4 * c, 4, 0x1000 + c * 4)
	end
	return f
end

FONT16 = makeFont(0x20, 0xFF, 16, 6, 4, 0, 1)  -- ascii: a=0 b=6 c=1; space w=4
FONT16B = makeFont(0x20, 0xFF, 16, 10, 5, 0, 1) -- "font2" for WordWrap2 tests

local pagesMade = {}
Game = setmetatable({}, {__index = function(_, k)
	if k == "LoadDataFileFromLod" then
		return function(name)
			if pagesMade[name] then
				return pagesMade[name]
			end
			local tag, hi = name:match("^DBCS_(%w+)_(%x+)%.fnt$")
			assert(tag, "unexpected lod load: " .. tostring(name))
			local h = tonumber(tag:match("%d+"))
			local f = makeFont(0, 255, h, h, h, 0, 0) -- CJK: square glyphs, a=c=0
			pagesMade[name] = f
			return f
		end
	elseif k == "CanLoadFileFromLod" then
		return function(name) return true end
	elseif k:match("_fnt$") then
		return 0
	end
	return nil
end})

events = setmetatable({}, {__newindex = function(t, k, v)
	local list = rawget(t, "_" .. k) or {}
	list[#list + 1] = v
	rawset(t, "_" .. k, list)
end})
Message = function(s) LASTMSG = s end
offsets = {MMVersion = 8}
Party = {}

-- ===== load the real file =====
dofile(SCRIPT_UNDER_TEST)

-- ===== test framework =====
local pass, fail = 0, 0
local function check(name, cond, extra)
	if cond then
		pass = pass + 1
		print("PASS " .. name)
	else
		fail = fail + 1
		print("FAIL " .. name .. (extra and ("  -> " .. tostring(extra)) or ""))
	end
end

local NEXTS = 0x03000000
local function putStr(s)
	local p = NEXTS
	NEXTS = NEXTS + 0x1000
	mem.copy(p, s .. "\0")
	return p
end

local DLG = 0x04000000
local function setDlgW(w) wr(DLG + 8, 4, w) end

local WRAPBUF = 0x5DC8E0
local GetLineWidth, WordWrap, WordWrap2 = 0x449C7B, 0x449ECA, 0x44A058

local DEFCALL
local function def(...)
	DEFCALL = {...}
	return 4242
end

-- gb2312 bytes: 你=C4E3 好=BAC3 ，=A3AC (noStart) 《=A1B6 (noEnd)
local NI, HAO, COMMA, LQUO = "\196\227", "\186\195", "\163\172", "\161\182"

-- ===== install sanity =====
check("install: hookfunction x3", HF[GetLineWidth] ~= nil and HF[WordWrap] ~= nil and HF[WordWrap2] ~= nil)
check("install: asmpatch count 9 (3L + 5 loops + A)", #PATCHES == 9, #PATCHES)
check("install: asmhook count 1 (L4)", #ASMHOOKS == 1, #ASMHOOKS)
check("install: loop hooks registered", (function()
	local n = 0
	for _ in pairs(HOOKS) do n = n + 1 end
	return n == 5
end)(), nil)
check("install: hf arg counts", HF[WordWrap].nstack == 3 and HF[WordWrap2].nstack == 4 and HF[GetLineWidth].nstack == 0)

-- ===== B: GetLineWidth =====
DEFCALL = nil
local r = HF[GetLineWidth].f(nil, def, FONT16, putStr("Hello"))
check("B: pure ascii uses def()", r == 4242 and DEFCALL ~= nil)

r = HF[GetLineWidth].f(nil, def, FONT16, putStr(NI .. HAO))
check("B: 2 CJK chars = 32", r == 32, r)

r = HF[GetLineWidth].f(nil, def, FONT16, putStr("A" .. NI))
check("B: 'A'+CJK = 7+16 = 23", r == 23, r)

r = HF[GetLineWidth].f(nil, def, FONT16, putStr(NI .. "\n" .. NI))
check("B: stops at newline = 16", r == 16, r)

r = HF[GetLineWidth].f(nil, def, FONT16, putStr(NI .. "\12" .. "01234" .. NI))
check("B: color code skipped = 32", r == 32, r)

-- ===== C: WordWrap =====
local function wrap(s, W, x, keepR, font)
	setDlgW(W)
	local p = HF[WordWrap].f(nil, def, putStr(s), font or FONT16, DLG, x or 0, keepR or 0)
	if p == WRAPBUF then
		return mem.string(p), p
	end
	return mem.string(p), p
end

DEFCALL = nil
local out, ptr = wrap("hello world", 50)
check("C: pure ascii uses def()", ptr == 4242 and DEFCALL ~= nil)

out = wrap(NI .. HAO .. NI .. HAO .. NI .. HAO .. NI .. HAO .. NI .. HAO, 50)
check("C: CJK wrap lines of 3+3+3+1", out == NI .. HAO .. NI .. "\n" .. HAO .. NI .. HAO .. "\n" .. NI .. HAO .. NI .. "\n" .. HAO,
	(out:gsub("[^\10]", "x")))
check("C: all lines break on pair boundary", (function()
	for line in out:gmatch("[^\n]+") do
		if #line % 2 ~= 0 then return false end
	end
	return true
end)())

out = wrap(NI .. HAO .. NI .. COMMA .. HAO .. HAO, 50)
check("C: kinsoku comma hangs at line end", out:match("^" .. NI .. HAO .. NI .. COMMA .. "\n") ~= nil, out:gsub("\n", "|"))

out = wrap(NI .. HAO .. NI .. LQUO .. HAO .. HAO, 50)
check("C: kinsoku open-quote pushed to next line", out:match("\n" .. LQUO) ~= nil, out:gsub("\n", "|"))

out = wrap(NI .. " def " .. HAO .. HAO .. HAO, 50)
check("C: break replaces space", out:find(" \n") == nil and out:find("\n") ~= nil, out:gsub("\n", "|"))
check("C: ascii word not split", out:find("def") ~= nil)

out = wrap("\9" .. "100" .. NI .. "x" .. HAO, 300)
check("C: tab code passes through", out:find("\9" .. "100", 1, true) ~= nil)

local orig = putStr(NI .. "\13" .. "abc")
setDlgW(50)
local p2 = HF[WordWrap].f(nil, def, orig, FONT16, DLG, 0, 0)
check("C: \\r returns original ptr unwrapped", p2 == orig)

out = wrap(NI .. "\n" .. NI .. HAO .. NI .. HAO, 50)
check("C: existing newline resets line", out == NI .. "\n" .. NI .. HAO .. NI .. "\n" .. HAO, out:gsub("\n", "|"))

-- legacy marker bridge
local marked = "\14\32\14" .. NI .. "\7\32\14" .. HAO .. "\7\15"
check("C: legacy markers decoded", DBCS.decodeSpecial(marked) == NI .. HAO, DBCS.decodeSpecial(marked))
out = wrap(marked .. marked .. marked .. marked .. marked, 50)
check("C: marked text wraps as plain", out:find("\14") == nil and out:find("\n") ~= nil, out)

-- ===== C': WordWrap2 =====
setDlgW(50)
local s9 = "_" .. NI .. HAO .. NI .. HAO .. NI .. HAO
local p3 = HF[WordWrap2].f(nil, def, putStr(s9), FONT16, FONT16B, DLG, 0, 0)
local out2 = mem.string(p3)
check("C': font2 segment breaks re-open with _", out2:find("\n_", 1, true) ~= nil, out2:gsub("\n", "|"))

-- ===== D: draw loop handler =====
local dproc = ASMPROCS[1].p -- loop procs first now; TestChar proc is last
local EBP = 0x02000000
local sptr = putStr(NI .. HAO)
mem.i4[EBP - 4] = sptr
mem.i4[EBP + 0x14] = 0
mem.i4[EBP - 0xC] = 4
mem.u2[EBP + 0x10] = 0x1234
mem.u2[EBP + 0x20] = 7
mem.i4[EBP + 0x18] = 0
CALLS = {}
local d = {cl = 0xC4, ebx = FONT16, esi = 100, edi = 50, ebp = EBP}
HOOKS[dproc](d)
local c = CALLS[#CALLS]
check("D: shadow blit called", c ~= nil and c[1] == 0x4A4E9F, c and c[1])
check("D: blit x,y", c and c[4] == 100 and c[5] == 50, c and (c[4] .. "," .. c[5]))
check("D: blit w,h = 16,16", c and c[7] == 16 and c[8] == 16)
check("D: blit color,shadow", c and c[10] == 0x1234 and c[11] == 7)
check("D: pen advanced to 116", d.esi == 116, d.esi)
check("D: index bumped for pair", mem.i4[EBP + 0x14] == 1, mem.i4[EBP + 0x14])

-- D with plain color 0 -> plain blitter
mem.u2[EBP + 0x10] = 0
mem.i4[EBP + 0x14] = 0
CALLS = {}
d = {cl = 0xC4, ebx = FONT16, esi = 0, edi = 0, ebp = EBP}
HOOKS[dproc](d)
c = CALLS[#CALLS]
check("D: color 0 uses plain blitter", c and c[1] == 0x4A4D01, c and c[1])

-- D invalid trail byte: no blit, no extra bump
local sbad = putStr("\196A")
mem.i4[EBP - 4] = sbad
mem.i4[EBP + 0x14] = 0
mem.i4[EBP - 0xC] = 2
CALLS = {}
d = {cl = 0xC4, ebx = FONT16, esi = 0, edi = 0, ebp = EBP}
HOOKS[dproc](d)
check("D: invalid pair skipped safely", #CALLS == 0 and mem.i4[EBP + 0x14] == 0 and d.esi == 0)

-- ===== G: centered line handler =====
local gproc = ASMPROCS[5].p
mem.i4[EBP + 0x10] = sptr
mem.i4[EBP - 8] = 4
mem.i4[EBP + 0xC] = 30
mem.i4[EBP - 4] = 0 -- color 0 -> 0xFFFF
CALLS = {}
d = {eax = 0xC4, ebx = 0, esi = FONT16, edi = 200, ebp = EBP}
HOOKS[gproc](d)
c = CALLS[#CALLS]
check("G: blit shadow variant with color FFFF", c and c[1] == 0x4A4E9F and c[10] == 0xFFFF, c and c[10])
check("G: y from frame +30", c and c[5] == 30, c and c[5])
check("G: index in ebx bumped", d.ebx == 1, d.ebx)
check("G: pen 200 -> 216", d.edi == 216, d.edi)

-- ===== F: scroll buffer handler =====
local fproc = ASMPROCS[4].p
mem.i4[EBP + 0x10] = sptr
mem.i4[EBP - 4] = 0
mem.i4[EBP - 0xC] = 4
mem.i4[EBP - 8] = 0x1111
mem.i4[EBP + 0x14] = 640
CALLS = {}
d = {eax = 0xC4, esi = FONT16, edi = 0x08000000, ebp = EBP}
HOOKS[fproc](d)
c = CALLS[#CALLS]
check("F: buffer blit called", c and c[1] == 0x410AA5, c and c[1])
check("F: pitch*2 passed", c and c[9] == 1280, c and c[9])
check("F: dest advanced by 32 bytes", d.edi == 0x08000000 + 32, d.edi)
check("F: index bumped", mem.i4[EBP - 4] == 1)

-- ===== E1: truncate-measure handler =====
local e1proc = ASMPROCS[2].p
mem.copy(0x5E1020, NI .. HAO .. "\0")
mem.i4[EBP + 0x14] = 0
mem.i4[EBP - 4] = 4
d = {cl = 0xC4, edi = FONT16, esi = 5, ebp = EBP}
HOOKS[e1proc](d)
check("E1: width accumulated 5+16", d.esi == 21, d.esi)
check("E1: index bumped", mem.i4[EBP + 0x14] == 1)

-- ===== E2: limited inline draw handler =====
local e2proc = ASMPROCS[3].p
mem.i4[EBP + 0x14] = 0
mem.i4[EBP + 0x18] = 0
mem.i4[EBP - 4] = 4
mem.u2[EBP + 0x10] = 0
CALLS = {}
d = {eax = 0xC4, edi = FONT16, esi = 10, ebx = 20, ebp = EBP}
HOOKS[e2proc](d)
c = CALLS[#CALLS]
check("E2: plain blit at 10,20", c and c[1] == 0x4A4D01 and c[4] == 10 and c[5] == 20)
check("E2: both indexes bumped", mem.i4[EBP + 0x14] == 1 and mem.i4[EBP + 0x18] == 1)

-- ===== page eviction self-heal =====
-- clobber the page header for 你 (DBCS_16_C4.fnt): draw must degrade to a tofu
-- advance without blitting; restoring the header must bring glyphs back
local pageC4 = pagesMade["DBCS_16_C4.fnt"]
local savedH = mem.u1[pageC4 + 5]
mem.u1[pageC4 + 5] = 99
mem.i4[EBP - 4] = sptr
mem.i4[EBP - 0xC] = 4
mem.i4[EBP + 0x14] = 0
mem.u2[EBP + 0x10] = 0x1234
CALLS = {}
d = {cl = 0xC4, ebx = FONT16, esi = 50, edi = 0, ebp = EBP}
HOOKS[dproc](d)
check("evict: no blit on dead page", #CALLS == 0, #CALLS)
check("evict: tofu advance 50+16", d.esi == 66, d.esi)
check("evict: pair still consumed", mem.i4[EBP + 0x14] == 1)
mem.u1[pageC4 + 5] = savedH
mem.i4[EBP + 0x14] = 0
CALLS = {}
d = {cl = 0xC4, ebx = FONT16, esi = 50, edi = 0, ebp = EBP}
HOOKS[dproc](d)
c = CALLS[#CALLS]
check("evict: self-heals after restore", c ~= nil and c[1] == 0x4A4E9F, c and c[1])
check("evict: pen advance restored", d.esi == 66, d.esi)

-- ===== M: direct-draw marker bridge =====
local marked2 = "\14\32\14" .. NI .. "\7\32\14" .. HAO .. "\7\15"
local mstr = putStr(marked2)
DEFCALL = nil
HF[0x44A50F].f(nil, def, DLG, FONT16, 1, 2, 3, mstr, 0, 5, 0)
check("M1: def called with scratch ptr", DEFCALL ~= nil and DEFCALL[6] ~= mstr, DEFCALL and DEFCALL[6])
check("M1: scratch holds decoded text", DEFCALL ~= nil and mem.string(DEFCALL[6]) == NI .. HAO, DEFCALL and mem.string(DEFCALL[6]))
DEFCALL = nil
local plain = putStr("plain")
HF[0x44A50F].f(nil, def, DLG, FONT16, 1, 2, 3, plain, 0, 5, 0)
check("M1: plain text passed through untouched", DEFCALL ~= nil and DEFCALL[6] == plain)
DEFCALL = nil
HF[0x44A253].f(nil, def, DLG, FONT16, 1, 2, 3, mstr, 100, 0)
check("M2: def called with decoded scratch", DEFCALL ~= nil and mem.string(DEFCALL[6]) == NI .. HAO)

-- ===== wrap output cap =====
local big = string.rep(NI, 2600) -- 5200 bytes > 4095
out = wrap(big, 100)
check("cap: output clamped under 4096", #out <= 4095, #out)

print(string.format("== %d passed, %d failed ==", pass, fail))
if fail > 0 then os.exit(1) end
