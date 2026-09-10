-- Korean full-screen cutscene subtitles for MM8 / MMMerge.
-- Source SRT files are UTF-8. Runtime text is converted to Windows CP949
-- before it reaches the native EUC-KR/DBCS renderer.

KoreanMovieSubtitles = KoreanMovieSubtitles or {}
local KMS = KoreanMovieSubtitles

KMS.Version = "1.1"
KMS.Settings = KMS.Settings or {
    X = 32,
    Y = 394,
    Width = 576,
    Height = 78,
    Shift = 3,
    Font = nil,
    Color = 0xFFFF,
    ShadowColor = 0,
    ShadowOffset = 1,
    StartGraceMs = 750
}

local SUBTITLE_FILES = {
    ["6intro"] = "Data/Korean Subtitles/mm6/6intro.srt",
    ["citytrtr"] = "Data/Korean Subtitles/mm6/citytrtr.srt",
    ["mm6end1"] = "Data/Korean Subtitles/mm6/mm6end1.srt",
    ["7intro"] = "Data/Korean Subtitles/mm7/7intro.srt",
    ["7losegame"] = "Data/Korean Subtitles/mm7/7losegame.srt",
    ["arbiter evil"] = "Data/Korean Subtitles/mm7/arbiter evil.srt",
    ["arbiter good"] = "Data/Korean Subtitles/mm7/arbiter good.srt",
    ["endgame 1 good"] = "Data/Korean Subtitles/mm7/endgame 1 good.srt",
    ["family reunion"] = "Data/Korean Subtitles/mm7/family reunion.srt",
    ["intro post"] = "Data/Korean Subtitles/mm7/intro post.srt",
    ["mm3 people evil"] = "Data/Korean Subtitles/mm7/mm3 people evil.srt",
    ["mm3 people good"] = "Data/Korean Subtitles/mm7/mm3 people good.srt",
    ["pcout01"] = "Data/Korean Subtitles/mm7/pcout01.srt",
    ["dragonhunters"] = "Data/Korean Subtitles/mm8/DragonHunters.srt",
    ["confluxkey"] = "Data/Korean Subtitles/mm8/confluxkey.srt",
    ["dragonsrevenge"] = "Data/Korean Subtitles/mm8/dragonsrevenge.srt",
    ["overrept"] = "Data/Korean Subtitles/mm8/overrept.srt",
    ["skeltrans"] = "Data/Korean Subtitles/mm8/skeltrans.srt",
    ["wingame"] = "Data/Korean Subtitles/mm8/wingame.srt"
}

local cache = {}
local active = nil
local warnedConversion = false
local warnedRender = false
local warnedNativeHook = false
local nativeFrameHooksInstalled = false

-- MM8/GrayFace movie rendering is synchronous: events.ShowMovie fires before
-- the native player enters its blocking Bink/Smacker loop, while the normal
-- game PostRender hook does not run for those movie frames.  These are the two
-- draw-call sites used by the patched MM8 executable.  We hook the instruction
-- immediately after each CALL so the subtitle is painted after the movie frame.
local NATIVE_MOVIE_DRAW_CALLS = {
    0x4BC9C7, -- Bink draw call (next instruction: 0x4BC9CC)
    0x4BCBE6  -- Smacker draw call (next instruction: 0x4BCBEB)
}

local function logMessage(message)
    if Log and Merge and Merge.Log then
        pcall(Log, Merge.Log.Info, "%s", "[KoreanMovieSubtitles] " .. message)
    else
        pcall(print, "[KoreanMovieSubtitles] " .. message)
    end
end

local function trim(s)
    return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function normalizeMovieName(name)
    if type(name) ~= "string" then
        return ""
    end
    name = trim(name:gsub("%z", "")):gsub("\\", "/")
    name = name:match("([^/]+)$") or name
    name = trim(name)
    if #name >= 2 and name:sub(1, 1) == '"' and name:sub(-1) == '"' then
        name = name:sub(2, -2)
    end
    name = trim(name)
    name = name:gsub("%.[^%.]+$", "")
    return string.lower(trim(name))
end

local function parseTimestamp(value)
    local h, m, s, ms = value:match("^(%d+):(%d+):(%d+),(%d+)$")
    if not h then
        h, m, s, ms = value:match("^(%d+):(%d+):(%d+)%.(%d+)$")
    end
    if not h then
        return nil
    end
    return (((tonumber(h) * 60 + tonumber(m)) * 60 + tonumber(s)) * 1000 + tonumber(ms))
end

local function toGameEncoding(text)
    if type(string.convert) ~= "function" then
        if not warnedConversion then
            warnedConversion = true
            logMessage("string.convert is unavailable; subtitles are disabled to avoid feeding UTF-8 into the DBCS renderer.")
        end
        return nil
    end
    local ok, converted = pcall(string.convert, text, "utf8", 949)
    if not ok or type(converted) ~= "string" then
        if not warnedConversion then
            warnedConversion = true
            logMessage("UTF-8 to CP949 conversion failed; subtitles are disabled for this cue.")
        end
        return nil
    end
    return converted
end

local function parseSrt(raw)
    if type(raw) ~= "string" then
        return nil, "SRT data is not a string"
    end
    if raw:sub(1, 3) == "\239\187\191" then
        raw = raw:sub(4)
    end
    raw = raw:gsub("\r\n", "\n"):gsub("\r", "\n") .. "\n\n"

    local cues = {}
    for block in raw:gmatch("(.-)\n\n+") do
        if block:match("%S") then
            local lines = {}
            for line in block:gmatch("[^\n]+") do
                lines[#lines + 1] = line
            end
            local timingIndex = 1
            if lines[1] and lines[1]:match("^%s*%d+%s*$") then
                timingIndex = 2
            end
            local timing = lines[timingIndex] or ""
            local a, b = timing:match("^%s*(%d+:%d+:%d+[,%.]%d+)%s+%-%->%s+(%d+:%d+:%d+[,%.]%d+)")
            local startMs = a and parseTimestamp(a) or nil
            local endMs = b and parseTimestamp(b) or nil
            if startMs and endMs and endMs > startMs then
                local textLines = {}
                for i = timingIndex + 1, #lines do
                    textLines[#textLines + 1] = lines[i]
                end
                local utf8Text = table.concat(textLines, "\n")
                if utf8Text ~= "" then
                    local encoded = toGameEncoding(utf8Text)
                    if encoded then
                        cues[#cues + 1] = {
                            Start = startMs,
                            Finish = endMs,
                            Text = encoded,
                            Utf8 = utf8Text
                        }
                    end
                end
            end
        end
    end
    if #cues == 0 then
        return nil, "no valid cues"
    end
    table.sort(cues, function(a, b) return a.Start < b.Start end)
    return cues
end

local function loadSubtitle(stem)
    stem = normalizeMovieName(stem)
    if cache[stem] ~= nil then
        return cache[stem] or nil
    end
    local filePath = SUBTITLE_FILES[stem]
    if not filePath then
        cache[stem] = false
        return nil
    end
    local f = io.open(filePath, "rb")
    if not f then
        cache[stem] = false
        logMessage("subtitle file not found: " .. filePath)
        return nil
    end
    local raw = f:read("*all")
    f:close()
    local cues, err = parseSrt(raw)
    if not cues then
        cache[stem] = false
        logMessage("could not parse " .. filePath .. ": " .. tostring(err))
        return nil
    end
    cache[stem] = cues
    return cues
end

local function findCue(cues, elapsedMs)
    if not cues then
        return nil
    end
    for i = 1, #cues do
        local cue = cues[i]
        if elapsedMs >= cue.Start and elapsedMs <= cue.Finish then
            return cue, i
        elseif cue.Start > elapsedMs then
            break
        end
    end
    return nil
end

local function elapsedMs(now, started)
    local delta = now - started
    if delta < 0 then
        delta = delta + 4294967296
    end
    return delta
end

local function startMovie(name)
    local stem = normalizeMovieName(name)
    local cues = loadSubtitle(stem)
    if not cues then
        active = nil
        return false
    end
    active = {
        Stem = stem,
        Cues = cues,
        Started = timeGetTime(),
        SeenPlaying = false
    }
    return true
end

local function stopMovie()
    active = nil
end

local function movieIsPlaying()
    if not Game or type(Game.IsMoviePlaying) ~= "function" then
        return true
    end
    local ok, playing = pcall(Game.IsMoviePlaying)
    return ok and not not playing
end

local function drawSubtitle(text)
    if not CustomUI or type(CustomUI.ShowText) ~= "function" or not Game then
        if not warnedRender then
            warnedRender = true
            logMessage("CustomUI.ShowText is unavailable; movie subtitles cannot be rendered.")
        end
        return false
    end
    local s = KMS.Settings
    local font = s.Font or Game.Lucida_fnt or Game.Arrus_fnt or Game.Smallnum_fnt
    if not font then
        return false
    end

    -- Draw a compact black outline first, then the centered white subtitle.
    local o = tonumber(s.ShadowOffset) or 1
    if o > 0 then
        CustomUI.ShowText(text, font, s.X, s.Y, s.Shift, s.Width, s.Height, -o, 0, s.ShadowColor, 0, false)
        CustomUI.ShowText(text, font, s.X, s.Y, s.Shift, s.Width, s.Height,  o, 0, s.ShadowColor, 0, false)
        CustomUI.ShowText(text, font, s.X, s.Y, s.Shift, s.Width, s.Height, 0, -o, s.ShadowColor, 0, false)
        CustomUI.ShowText(text, font, s.X, s.Y, s.Shift, s.Width, s.Height, 0,  o, s.ShadowColor, 0, false)
    end
    CustomUI.ShowText(text, font, s.X, s.Y, s.Shift, s.Width, s.Height, 0, 0, s.Color, 0, false)
    return true
end

local function drawActiveSubtitleFrame()
    if not active then
        return false
    end
    local cue = findCue(active.Cues, elapsedMs(timeGetTime(), active.Started))
    if cue then
        return drawSubtitle(cue.Text)
    end
    return false
end

local function installNativeMovieFrameHooks()
    if nativeFrameHooksInstalled then
        return true
    end
    if not mem or type(mem.autohook2) ~= "function" or not mem.u1 then
        return false
    end
    if Game and Game.Version and Game.Version ~= 8 then
        return false
    end

    local installed = 0
    for _, callAddress in ipairs(NATIVE_MOVIE_DRAW_CALLS) do
        local okRead, opcode = pcall(function() return mem.u1[callAddress] end)
        -- CALL rel32 is E8. Refuse to patch an unexpected executable layout.
        if okRead and opcode == 0xE8 then
            local okHook = pcall(mem.autohook2, callAddress + 5, drawActiveSubtitleFrame)
            if okHook then
                installed = installed + 1
            end
        end
    end

    nativeFrameHooksInstalled = installed > 0
    if not nativeFrameHooksInstalled and not warnedNativeHook then
        warnedNativeHook = true
        logMessage("native movie draw sites were not recognized; falling back to PostRender subtitles.")
    end
    KMS.NativeFrameHooksInstalled = nativeFrameHooksInstalled
    KMS.NativeFrameHookCount = installed
    return nativeFrameHooksInstalled
end

function events.ShowMovie(t)
    if type(t) == "table" then
        startMovie(t.Name)
    end
end

function events.PostRender()
    if not active then
        return
    end

    local now = timeGetTime()
    local elapsed = elapsedMs(now, active.Started)
    local playing = movieIsPlaying()
    if playing then
        active.SeenPlaying = true
    elseif active.SeenPlaying or elapsed > (KMS.Settings.StartGraceMs or 750) then
        stopMovie()
        return
    end

    -- Keep this path as a fallback for builds whose movie player yields to the
    -- regular renderer. The native Bink/Smacker hooks above handle Rodril's
    -- synchronous full-screen movie loops.
    drawActiveSubtitleFrame()
end

function events.GameInitialized2()
    installNativeMovieFrameHooks()
end

KMS.SubtitleFiles = SUBTITLE_FILES
KMS.NormalizeMovieName = normalizeMovieName
KMS.ParseTimestamp = parseTimestamp
KMS.ParseSrt = parseSrt
KMS.Load = loadSubtitle
KMS.FindCue = findCue
KMS.StartMovie = startMovie
KMS.StopMovie = stopMovie
KMS.DrawSubtitle = drawSubtitle
KMS.DrawActiveSubtitleFrame = drawActiveSubtitleFrame
KMS.InstallNativeMovieFrameHooks = installNativeMovieFrameHooks
KMS.NativeMovieDrawCalls = NATIVE_MOVIE_DRAW_CALLS
KMS.GetActive = function() return active end

-- Install as soon as General scripts load, before a new-game continent intro can
-- enter the blocking native movie loop. GameInitialized2 retries on odd builds.
installNativeMovieFrameHooks()
