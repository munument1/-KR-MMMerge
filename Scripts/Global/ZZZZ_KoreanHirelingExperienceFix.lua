-- Correct Rodril MMMerge's Scholar/Teacher/Instructor experience bonuses.
--
-- Upstream NPCFollowersSkills.lua adds +5/+10/+15 to the raw Learning skill
-- rank. Learning mastery then multiplies those values, so hiring all three can
-- appear as +60 on an Expert character instead of the advertised flat +30%
-- experience bonus. Keep the upstream follower system intact, remove only
-- these raw Learning ranks, then add the same values after Learning mastery is
-- calculated by GetLearningTotalSkill.

KoreanHirelingExperienceFix = KoreanHirelingExperienceFix or {}

local HIRELING_EXPERIENCE_BONUSES = {
    [4] = 5,   -- Scholar
    [13] = 10, -- Teacher
    [14] = 15  -- Instructor
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

local function removeRawLearningBonus(t)
    if not t or not const or not const.Skills or t.Skill ~= const.Skills.Learning then
        return
    end

    local bonus = getHirelingExperienceBonus()
    if bonus <= 0 then
        return
    end

    local level, mastery = SplitSkill(t.Result)
    t.Result = JoinSkill(math.max(0, level - bonus), mastery)
end

local function addFlatExperienceBonus(t)
    if not t then
        return
    end

    local bonus = getHirelingExperienceBonus()
    if bonus > 0 then
        t.Result = t.Result + bonus
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

-- This file is deliberately named ZZZZ_* in Scripts/Global so its GetSkill
-- handler is registered after Rodril's NPCFollowersSkills.lua handler.
function events.GetSkill(t)
    removeRawLearningBonus(t)
end

function events.GetLearningTotalSkill(t)
    addFlatExperienceBonus(t)
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
KoreanHirelingExperienceFix.RemoveRawLearningBonus = removeRawLearningBonus
KoreanHirelingExperienceFix.AddFlatExperienceBonus = addFlatExperienceBonus
KoreanHirelingExperienceFix.ApplyDescriptions = applyHirelingExperienceDescriptions
