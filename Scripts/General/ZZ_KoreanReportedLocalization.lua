-- Targeted fixes for player-reported strings that are not owned by the normal
-- localization tables. Keep this file narrow: exact UI literals, continent
-- chooser labels, and the MM7 history foreword only.

KoreanReportedLocalization = KoreanReportedLocalization or {}

local function encodeKorean(text)
    if KoreanText and KoreanText.EncodeOnce then
        return KoreanText.EncodeOnce(text)
    end
    return text
end

local UI_TEXT = {
    ["Free class / portrait combinations are allowed now."] = "이제 클래스/초상화 조합을 자유롭게 선택할 수 있습니다.",
    ["Free class/portrait combinations are allowed now."] = "이제 클래스/초상화 조합을 자유롭게 선택할 수 있습니다.",
    ["Interface:"] = "인터페이스:",
    ["Interface"] = "인터페이스",
    ["UI depends on continent"] = "대륙에 따라 UI 변경",
    ["Increase view range"] = "시야 거리 증가",
    ["Smaller potion bottles"] = "작은 물약병",
    ["Interface settings"] = "인터페이스 설정",
    ["Interface Settings"] = "인터페이스 설정",
    ["Extra settings"] = "추가 설정",
    ["Extra Settings"] = "추가 설정"
}

local function translateUI(text)
    if type(text) ~= "string" then
        return text
    end
    local localized = UI_TEXT[text]
    if localized then
        return encodeKorean(localized)
    end
    return text
end

-- Merge creates the Extra Settings / Controls additions through CustomUI.
-- Wrap only exact player-facing literals so logic keys and unrelated strings
-- are never altered.
local function installCustomUIHooks()
    if not CustomUI or KoreanReportedLocalization.CustomUIHooksInstalled then
        return
    end

    if type(CustomUI.CreateText) == "function" then
        local originalCreateText = CustomUI.CreateText
        CustomUI.CreateText = function(settings, ...)
            if type(settings) == "table" and type(settings.Text) == "string" then
                settings.Text = translateUI(settings.Text)
            end
            return originalCreateText(settings, ...)
        end
    end

    if type(CustomUI.DisplayTooltip) == "function" then
        local originalDisplayTooltip = CustomUI.DisplayTooltip
        CustomUI.DisplayTooltip = function(text, ...)
            return originalDisplayTooltip(translateUI(text), ...)
        end
    end

    KoreanReportedLocalization.CustomUIHooksInstalled = true
end

installCustomUIHooks()

-- The stock continent chooser uses picture-only buttons. Add a compact game
-- number to each globe so players who do not know the continent names can see
-- immediately which Might & Magic campaign they are starting.
local function installContinentGameLabels()
    if KoreanReportedLocalization.ContinentLabelsInstalled or
            not CustomUI or type(CustomUI.CreateText) ~= "function" or
            not const or not const.Screens or not const.Screens.ChooseContinent or
            not Game or not Game.Smallnum_fnt then
        return
    end

    local screen = const.Screens.ChooseContinent
    local labels = {
        {Text = "M&M 8", X = 290, Y = 207}, -- Jadame
        {Text = "M&M 7", X = 404, Y = 404}, -- Antagarich
        {Text = "M&M 6", X = 176, Y = 404}  -- Enroth
    }

    for index, label in ipairs(labels) do
        CustomUI.CreateText{
            Key = "KoreanContinentGameLabel" .. index,
            Text = label.Text,
            Font = Game.Smallnum_fnt,
            ColorStd = 0xFFFF,
            AlignLeft = true,
            Layer = 2,
            Screen = screen,
            X = label.X,
            Y = label.Y,
            Width = 70,
            Height = 16
        }
    end

    KoreanReportedLocalization.ContinentLabelsInstalled = true
end

-- The compact MM7 history table embedded in the Korean LOD is intentionally
-- retained because loading the full history source can exceed an engine-side
-- buffer. The full source translation already contains the foreword, so copy
-- only record 1 after the compact table has been loaded.
local MM7_FOREWORD = {
    Title = "저자의 서문",
    Text = "마크햄 경은 미래 세대들이 이곳에서 벌어지는 위대한 일들을 잊지 않도록 하몬데일 성과 그 소유주들에 대한 이 역사를 작성해 달라고 내게 부탁했다. 이 임무에 충실할 수 있기를 바란다. 주요 사건들이 일어날 때마다 그것이 좋든 나쁘든 가능한 한 충실하게 이 책에 기록할 것을 믿어도 좋다. 이곳에서 일어나는 일을 판단하는 것은 내 역할이 아니며, 오직 기록할 뿐이다.\n\n프로비던스가 우리에게 미소 짓기를!\n\n웬델 트위드\n궁정 역사가"
}

local function applyMM7Foreword()
    if not Game or not Game.HistoryTxt or not Game.HistoryTxt[1] or
            not TownPortalControls or not Map then
        return
    end

    local ok, continent = pcall(TownPortalControls.MapOfContinent, Map.MapStatsIndex)
    if ok and continent == 2 then
        Game.HistoryTxt[1].Title = encodeKorean(MM7_FOREWORD.Title)
        Game.HistoryTxt[1].Text = encodeKorean(MM7_FOREWORD.Text)
    end
end

function events.GameInitialized2()
    -- Some Merge builds initialize CustomUI later than script load. The
    -- continent chooser screen is also created by MenuChooseContinent here.
    installCustomUIHooks()
    installContinentGameLabels()
end

function events.LoadMap()
    applyMM7Foreword()
end

function events.AfterLoadMap()
    applyMM7Foreword()
end

KoreanReportedLocalization.TranslateUI = translateUI
KoreanReportedLocalization.ApplyMM7Foreword = applyMM7Foreword
KoreanReportedLocalization.InstallContinentGameLabels = installContinentGameLabels
