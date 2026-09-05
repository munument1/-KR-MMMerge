-- Opt-in MM8 UI diagnostics. Records state; never resets render flags/buffers.
-- Native probe only wraps Begin2D after checking its six original entry bytes.
-- End2D already contains Merge's InterfaceManager hook: observe FGInterfaceUpd
-- there instead of installing a second overlapping hook.
if not offsets or offsets.MMVersion ~= 8 or KoreanUIDiagnostics then return end

local options = {Enabled = 0, NativeBegin2D = 0}
local ini = io.open('Data/KO_UIDiagnostics.ini', 'r')
if ini then
    for line in ini:lines() do
        local key, value = line:match('^%s*(%w+)%s*=%s*(%d+)')
        if key and options[key] ~= nil then options[key] = tonumber(value) end
    end
    ini:close()
end
if options.Enabled ~= 1 then return end

local D = {Version = 'ui-test1', NativeProbe = 'off', Errors = 0}
KoreanUIDiagnostics = D
local SCREEN, BEGIN = 0xEC1980, 0x4A2FF2
local MAX_BYTES, MAX_QUEUE = 2 * 1024 * 1024, 256
local queue, qfirst, qcount = {}, 1, 0
local recent, rfirst, rcount = {}, 1, 0
local lastSample, lastFlush = {}, 0
local beginCalls, beginFailures = 0, 0
local now = timeGetTime or function() return os.time() * 1000 end
local logPath = 'KO_UI_Diagnostic.log'
local pendingMarker = false

local function clean(s)
    return tostring(s):gsub('[\r\n\t]', ' '):sub(1, 250)
end
local function read(obj, key)
    local ok, value = pcall(function() return obj[key] end)
    return ok and clean(value) or 'unavailable'
end
local function enqueue(line)
    if qcount == MAX_QUEUE then
        queue[qfirst] = nil; qfirst = qfirst % MAX_QUEUE + 1; qcount = qcount - 1
    end
    queue[(qfirst + qcount - 1) % MAX_QUEUE + 1] = line
    qcount = qcount + 1
    if rcount == 120 then
        recent[rfirst] = nil; rfirst = rfirst % 120 + 1; rcount = rcount - 1
    end
    recent[(rfirst + rcount - 1) % 120 + 1] = line
    rcount = rcount + 1
end
local function appendBounded(path, text)
    local f = io.open(path, 'rb')
    local size = f and f:seek('end') or 0
    if f then f:close() end
    if size + #text > MAX_BYTES then
        os.remove(path .. '.previous')
        local ok = os.rename(path, path .. '.previous')
        if not ok then return false end -- do not truncate an unrotated log
    end
    f = io.open(path, 'ab')
    if not f then return false end
    local ok = f:write(text)
    f:close()
    return ok ~= nil
end

local memInfo, getMemory
pcall(function()
    getMemory = mem.dll.psapi.GetProcessMemoryInfo
    if getMemory then memInfo = mem.StaticAlloc(40) end
end)
local function usage()
    local s = ' luaKiB=' .. math.floor(collectgarbage('count'))
    if memInfo and getMemory then
        mem.u4[memInfo] = 40
        local ok, result = pcall(getMemory, -1, memInfo, 40)
        if ok and result ~= 0 then
            s = s .. ' workingSet=' .. mem.u4[memInfo + 12] .. ' pagefile=' .. mem.u4[memInfo + 32]
        end
    end
    if DBCS and DBCS.getWrapCacheStats then
        local c = DBCS.getWrapCacheStats()
        s = s .. ' cacheEntries=' .. c.entries .. ' cacheBytes=' .. c.bytes
    end
    if DBCS and DBCS.Diagnostics then
        s = s .. ' rendererErrors=' .. DBCS.Diagnostics.errors
            .. ' rendererLastError=' .. clean(DBCS.Diagnostics.lastError)
            .. ' rendererInstallError=' .. clean(DBCS.Diagnostics.installError)
    end
    return s
end
local function state(phase)
    local v = mem.i4
    local s = string.format('%s ms=%d phase=%s screen=%s map=%s count=%d buffer=%08X pitch=%d clip=%d,%d,%d,%d clipEnabled=%d',
        os.date('%Y-%m-%dT%H:%M:%S'), now(), phase,
        read(Game, 'CurrentScreen'), read(Map, 'Name'),
        v[SCREEN + 0x400E4], mem.u4[SCREEN + 0x400EC], v[SCREEN + 0x400F0],
        v[SCREEN + 0x400F8], v[SCREEN + 0x400F4], v[SCREEN + 0x40100], v[SCREEN + 0x400FC],
        v[SCREEN + 0x40104])
    return s .. ' beginCalls=' .. beginCalls .. ' beginFailed=' .. beginFailures
end
local function sample(phase, force)
    local t = now()
    if force or not lastSample[phase] or t - lastSample[phase] >= 5000 then
        lastSample[phase] = t
        enqueue(state(phase))
    end
end
local function safe(fn, ...)
    local ok, err = pcall(fn, ...)
    if not ok then D.Errors = D.Errors + 1; D.LastError = clean(err) end
end
local function flush(force)
    local t = now()
    if not force and t - lastFlush < 5000 then return end
    lastFlush = t
    enqueue(os.date('%Y-%m-%dT%H:%M:%S') .. ' phase=usage' .. usage()
        .. ' probeErrors=' .. D.Errors .. ' probe=' .. D.NativeProbe)
    local lines = {}
    for i = 0, qcount - 1 do lines[#lines + 1] = queue[(qfirst + i - 1) % MAX_QUEUE + 1] end
    if appendBounded(logPath, table.concat(lines, '\n') .. '\n') then
        queue, qfirst, qcount = {}, 1, 0
    end
end
function D.Mark()
    safe(function()
        sample('USER-MARK-outside-draw', true)
        local lines = {'=== USER MARK; preceding sampled phases (not every frame) ==='}
        for i = 0, rcount - 1 do lines[#lines + 1] = recent[(rfirst + i - 1) % 120 + 1] end
        appendBounded('KO_UI_Incident.log', table.concat(lines, '\n') .. '\n')
        pendingMarker = true
        flush(true)
    end)
end
function D.Snapshot() safe(sample, 'MANUAL-outside-draw', true); safe(flush, true) end

if options.NativeBegin2D == 1 then
    local ok, err = pcall(function()
        -- push ebp; mov ebp,esp; sub esp,7Ch. Skip changed/unknown entries.
        local expected = '\85\139\236\131\236\124'
        if mem.string(BEGIN, 6, true) ~= expected then
            D.NativeProbe = 'skipped-entry-signature-mismatch'; return
        end
        mem.hookfunction(BEGIN, 1, 0, function(d, def, this)
            -- Preserve the engine's original call and return value even if our
            -- logger fails. Never write to any member of the game Screen.
            if this == SCREEN then
                beginCalls = beginCalls + 1
                safe(sample, 'Begin2D-entry', false)
            end
            local result = def(this)
            if this == SCREEN then
                safe(function()
                    local failed = mem.i4[SCREEN + 0x400E4] == 0
                    if failed then beginFailures = beginFailures + 1 end
                    sample(failed and 'Begin2D-failed' or 'Begin2D-return', false)
                end)
            end
            return result
        end, 6)
        D.NativeProbe = 'Begin2D-installed'
    end)
    if not ok then D.NativeProbe = 'install-error:' .. clean(err) end
end

function events.BGInterfaceUpd() safe(sample, 'BGInterfaceUpd', false) end
function events.FGInterfaceUpd()
    safe(sample, 'FG-before-End2D', pendingMarker)
    pendingMarker = false
end
function events.Tick() safe(sample, 'Tick-outside-draw', false); safe(flush, false) end
function events.BeforeSaveGame() safe(sample, 'BeforeSaveGame', true); safe(flush, true) end
function events.LeaveMap() safe(sample, 'LeaveMap', true); safe(flush, true) end
function events.AfterLoadMap() safe(sample, 'AfterLoadMap', true); safe(flush, true) end
function events.KeyDown(t)
    if t.Key == 121 and t.Alt and not t.WasPressed and Keys.IsPressed(const.Keys.CTRL) then
        t.Handled = true
        D.Mark() -- Ctrl+Alt+F10; no dialog/sound/reset that could mask the bug.
    end
end
safe(function()
    enqueue('SESSION version=' .. D.Version .. ' renderer=' .. read(DBCS, 'SafetyRevision')
        .. ' nativeInstalled=' .. read(DBCS, 'NativeInstalled')
        .. ' UILayout=' .. read(Game and Game.PatchOptions, 'UILayout')
        .. ' probe=' .. D.NativeProbe)
    flush(true)
end)
