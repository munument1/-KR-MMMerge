#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
overlay = (root / 'Data/Text localization/KO_TransTxt.txt').read_bytes().decode('cp949')
ids = []
for line in overlay.splitlines()[1:]:
    parts = line.split('\t', 3)
    if len(parts) >= 4 and parts[1].strip().isdigit():
        ids.append(int(parts[1].strip()))
assert ids and ids[0] == 1, ids[:5]
assert 0 not in ids
assert 25 in ids and 41 in ids

runtime = (root / 'Scripts/General/ZZZZ_KoreanTransTxtIndexFix.lua').read_text('utf-8')
for token in ('Game.TransTxt[id]', 'KO_TransTxt.txt', 'events.GameInitialized1', 'events.GameInitialized2'):
    assert token in runtime, token
assert runtime.isascii(), 'runtime repair must stay ASCII-only'

builder = (root / 'tools/build_static_localization.py').read_text('utf-8')
assert 'record_base: int = 0' in builder
assert "apply_by_order(doc, overlay('KO_TransTxt.txt'), 1, trans_row, record_base=1)" in builder

# Direct unit test of the corrected row-order helper.
namespace = {}
exec(compile(builder, 'build_static_localization.py', 'exec'), namespace)
TsvDocument = namespace['TsvDocument']
apply_by_order = namespace['apply_by_order']
doc = TsvDocument('100\tA\n200\tB\n300\tC\n')
changed = apply_by_order(
    doc,
    {(1, ''): 'one', (2, ''): 'two', (3, ''): 'three'},
    1,
    lambda row, index: bool(row.fields and row.fields[0].isdigit()),
    record_base=1,
)
assert changed == 3
assert [row.fields[1] for row in doc.rows] == ['one', 'two', 'three']
print(f'Korean TransTxt index fix: OK ({len(ids)} overlay records; base=1)')
