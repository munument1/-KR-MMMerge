# Korean PO migration workflow

This repository is migrating the core MMMerge text catalog to GNU gettext PO
without replacing the existing Korean patch in one step.

## Why this is staged

The released patch currently mixes several localization mechanisms:

- `Data/Text localization/KO_*.txt` runtime tables
- translated text already packed in `Data/zz LocKO.T.lod` and
  `Data/zz LocKO.icons.lod`
- Lua-side runtime/cache repair code
- Korean-only UI images, fonts and gameplay/localization fixes

Replacing all of that with another project's build output at once would risk
losing working Korean fixes.  The PO migration therefore starts as a catalog
bridge and only becomes the source of truth after round-trip comparisons are
clean.

## Source of the Korean translations

`mm678-i18n` is used only as pinned extraction/template tooling.

The bootstrap workflow deliberately deletes its existing Korean PO, copies the
empty POT, and then harvests translations from **this repository's current
packaged Korean LOD files**.

No Korean `msgstr` from `mm678-i18n` is imported.

Pinned tooling revision:

`aea1b22666ef556f34a71b4f3945904b04de1466`

## Files

- `translations/ko/mm678.po` - generated/editable gettext catalog
- `translations/ko/PO_BASELINE.json` - initial coverage baseline
- `tools/po_catalog_stats.py` - completeness/regression audit
- `.github/workflows/bootstrap-po-catalog.yml` - one-time/rebuild bootstrap
- `.github/workflows/validate-po-catalog.yml` - PO validation

## Editing

After the bootstrap catalog exists, open `translations/ko/mm678.po` with
Poedit or another gettext editor.  The English source is `msgid`, the Korean
translation is `msgstr`, and `msgctxt` keeps context-sensitive strings apart.

At this migration stage, editing the PO does **not** change the released patch
automatically.  `Data/Text localization`, the LOD files, Lua scripts and the
existing release workflow remain authoritative until the next stage passes
round-trip checks.

## What CI checks

The local audit does not assume that an external PO checker implies complete
translation coverage.  It independently records and checks:

- active entry count
- reviewed translated count
- untranslated count
- fuzzy count
- duplicate `(msgctxt, msgid)` keys
- Unicode replacement characters

The validation workflow also runs the pinned `mm678-i18n` hard-error PO checks
for Korean only (placeholder set/order, bare tabs/CR, literal `\\n`, etc.).

## Migration stages

### Stage 1 - bootstrap (this change)

Current Korean LOD -> empty English POT -> `translations/ko/mm678.po`.
Existing release files are untouched.

### Stage 2 - build preview

PO -> generated MMMerge text tree.  Compare generated text against the current
Korean package and classify every difference instead of silently overwriting
files.

### Stage 3 - round-trip gate

For gettext-compatible text, require that PO -> game files reproduces the
approved Korean text.  Keep runtime-only/custom Lua localization outside the
PO where appropriate.

### Stage 4 - source-of-truth switch

Only after the round-trip gate is clean, make PO the editable source for core
text and generate the corresponding TXT/LOD artifacts during CI/release.

This also gives upstream-update detection: when English source entries change,
PO updates can add them as untranslated instead of allowing them to disappear
inside otherwise structurally valid TXT tables.
