-- Correct Rodril MMMerge's Scholar/Teacher/Instructor experience bonuses.
--
-- Rodril intentionally exposes these followers as +5/+10/+15 Learning in
-- GetSkill, which is also what the character sheet uses for the green skill
-- bonus display. Keep that display path untouched. Only normalize the final
-- GetLearningTotalSkill result so follower points stay flat percentage points
-- instead of being multiplied again by Learning mastery.

KoreanHirelingExperienceFix = KoreanHirelingExperienceFix or {}
KoreanHirelingExperienceFix.Version = "1.1"

local HIRELING_EXPERIENCE_BONUSES = {
    [4] = 5,   -- Scholar
    [13] = 10, -- Teacher
    [14] = 15  -- Instructor
}

local LEARNING_MASTERY_MULTIPLIERS = {
    [0] = 1,
    [1] = 1,
    [2] = 2,
    [3] = 3,
    [4] = 5
}

-- Keep runtime Korean text as EUC-KR decimal byte escapes. Scholar also keeps
-- Rodril's unlimited item-identification ability.
local HIRELING_EXPERIENCE_DESCRIPTIONS = {
    [4] = "\176\237\191\235 \193\223\191\161\180\194 \184\240\181\231 \196\179\184\175\197\205\192\199 \200\185\181\230 \176\230\199\232\196\161\176\161 5% \193\245\176\161\199\207\184\231 \190\198\192\204\197\219\192\187 \185\171\193\166\199\209\192\184\183\206 \189\196\186\176\199\213\180\207\180\217.",
    [13] = "\176\237\191\235 \193\223\191\161\180\194 \184\240\181\231 \196\179\184\175\197\205\192\199 \200\185\181\230 \176\230\199\232\196\161\176\161 10% \193\245\176\161\199\213\180\207\180\217.",
    [14] = "\176\237\191\235 \193\223\191\161\180\194 \184\240\181\231 \196\179\184\175\197\205\192\199 \200\185\181\230 \176\230\199\232\196\161\176\161 15% \193\245\176\161\199\213\180\207\180\217."
}

local function encodeKorean(text)
    if KoreanText and KoreanText.EncodeOnce then
        return KoreanText.EncodeOnce(text)
    end
    return text
end

local function getHirelingExperienceBonus()
    if not vars or not vars.NPCFollowers or not Game or not Game.NPC then
        return 0
    end

    local total = 0
    for _, npcId in pairs(vars.NPCFollowers) do
        local npc = Game.NPC[npcId]
        if npc then
            total = total + (HIRELING_EXPERIENCE_BONUSES[npc.Profession] or 0)
        end
    end
    return total
end

local function getLearningMasteryMultiplier(t)
    if not t or not const or not const.Skills then
        return 1
    end

    local player = t.Player
    if not player and t.PlayerIndex ~= nil and Party and Party.PlayersArray then
        player = Party.PlayersArray[t.PlayerIndex]
    end
    if not player or not player.Skills then
        return 1
    end

    local _, mastery = SplitSkill(player.Skills[const.Skills.Learning])
    return LEARNING_MASTERY_MULTIPLIERS[mastery] or 1
end

local function flattenHirelingExperienceBonus(t)
    if not t or t.Result == nil then
        return
    end

    local bonus = getHirelingExperienceBonus()
    if bonus <= 0 then
        return
    end

    local multiplier = getLearningMasteryMultiplier(t)
    if multiplier > 1 then
        t.Result = math.max(0, t.Result - bonus * (multiplier - 1))
    end
end

local function applyHirelingExperienceDescriptions()
    if not Game or not Game.NPCProf then
        return
    end

    for profession, description in pairs(HIRELING_EXPERIENCE_DESCRIPTIONS) do
        if Game.NPCProf[profession] then
            Game.NPCProf[profession].Description = encodeKorean(description)
        end
    end
end

-- Deliberately do NOT override events.GetSkill here. Rodril's own
-- NPCFollowersSkills.lua GetSkill handler owns the visible +5/+10/+15 Learning
-- bonus shown on the character sheet.
function events.GetLearningTotalSkill(t)
    flattenHirelingExperienceBonus(t)
end

function events.GameInitialized2()
    applyHirelingExperienceDescriptions()
end

function events.LoadMap()
    applyHirelingExperienceDescriptions()
end

function events.AfterLoadMap()
    applyHirelingExperienceDescriptions()
end

-- Re-apply immediately before NPC interaction as a final guard against an
-- earlier localization handler restoring the old raw-Learning description.
function events.EnterNPC()
    applyHirelingExperienceDescriptions()
end

KoreanHirelingExperienceFix.GetHirelingExperienceBonus = getHirelingExperienceBonus
KoreanHirelingExperienceFix.GetLearningMasteryMultiplier = getLearningMasteryMultiplier
KoreanHirelingExperienceFix.FlattenHirelingExperienceBonus = flattenHirelingExperienceBonus
KoreanHirelingExperienceFix.ApplyDescriptions = applyHirelingExperienceDescriptions
