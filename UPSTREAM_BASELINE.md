# MMMerge upstream baseline

This repository is a **Korean localization overlay**, not a fork or replacement distribution of MMMerge.

## Supported base

- Upstream project: `letr.rod/mmmerge`
- Upstream branch: `Rodril_nightly_build`
- Audited commit: `c0b6b4e9532e80413d1a3c27cbe25f57538c9a29`
- Audited commit date: 2024-10-30
- Upstream project URL: https://gitlab.com/letr.rod/mmmerge

The Korean patch is developed against Rodril's branch. Revamp, MAW, Waffle/community packs, and other derivatives are **not** the canonical base; compatibility with them must be handled as separate layers and must not silently redefine the base files in this repository.

## Overlay policy

1. Install a compatible Rodril MMMerge base first, then apply this Korean overlay.
2. Do not vendor or replace upstream gameplay scripts merely to change player-facing text.
3. Prefer Korean-only `Korean*` / `ZZ_Korean*` runtime overlays, localized table files, or generated localization archives.
4. If replacing an upstream path is unavoidable, document the exact upstream path, baseline commit, and reason here and cover it with regression tests.
5. Keep translation ownership in the canonical PO / generated Korean localization pipeline where possible; runtime rewrites are compatibility shims, not a second translation source.

## Intentional upstream overrides

### `Scripts/General/LocalizeTables.lua`

This is the **only intentional Rodril script-path replacement** currently kept by the Korean patch.

Rodril baseline file:
`Scripts/General/LocalizeTables.lua` at commit `c0b6b4e9532e80413d1a3c27cbe25f57538c9a29`.

The Korean version retains the upstream table-localization role but adds Korean encoding handling, runtime translation ownership, cache repair, continent-specific history handling, and other Korean-specific safeguards. Changes to this file must be reviewed as an upstream rebase rather than treated as an independent gameplay fork.

## Removed upstream overrides

### `Scripts/Maps/out01.lua`

Older Korean packages replaced Rodril's `out01.lua` solely to reuse localized `evt.str[13]` for two Dagger Wound Island cannon hints. The underlying Dimension Door and Town Portal gameplay code was otherwise identical to the Rodril baseline.

That localization has been moved to `Scripts/General/ZZ_KoreanDaggerWoundHints.lua`, so the Korean patch no longer replaces `Scripts/Maps/out01.lua`. Rodril now owns the map gameplay script completely.

## T.lod localization note

Rodril issue #17 discusses reworking the old localization system and warns that T.lod table-size mismatches can cause crashes. The issue remains open and describes an incomplete migration rather than a finished replacement contract.

For that reason this repository does **not** remove `Data/zz LocKO.T.lod` solely because of issue #17. Static localization remains on the current tested pipeline until the upstream localization contract changes or the Korean package completes and validates an equivalent migration.

## Updating the baseline

When `Rodril_nightly_build` moves:

1. Record the new upstream commit.
2. Diff upstream `Scripts/General/LocalizeTables.lua` against the Korean replacement.
3. Check for any new same-path collisions under `Scripts/`.
4. Run `python tools/validate_rodril_overlay_boundary.py`.
5. Run the existing localization, PO round-trip, native DBCS, and gameplay regression checks before changing the audited commit above.
