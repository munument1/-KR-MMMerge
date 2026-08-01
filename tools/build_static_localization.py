#!/usr/bin/env python3
"""Build a Korean Merge localization LOD from the current game's text skeleton.

The existing Korean LOD supplies fonts and translated map STR files.  This tool
adds only selected display-text tables rebuilt from the current mmmerge.T.lod;
gameplay columns are copied from that current skeleton without modification.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


DBCS_RE = re.compile(br"[\xA1-\xAC\xB0-\xC8\xCA-\xFD][\xA0-\xFF](?!\x07)")


def encode_dbcs_special(data: bytes) -> bytes:
    data = DBCS_RE.sub(lambda match: b"\x0e\x20\x0e" + match.group(0) + b"\x07\x0f", data)
    return data.replace(b"\x0f\x0e", b"")


def decode_dbcs_special(data: bytes) -> bytes:
    data = re.sub(br"\x20\x0e(..)\x07", lambda match: match.group(1), data)
    return re.sub(br"\x0e([^\x0f]+)\x0f", lambda match: match.group(1), data)


def encode_mixed_text(text: str) -> bytes:
    """Encode Korean as CP949 while preserving current Merge CP1252 glyphs."""
    output = bytearray()
    for index, char in enumerate(text):
        try:
            # Source tables are CP1252. Prefer that byte representation for
            # shared punctuation (ellipsis, smart quotes, etc.) so protected
            # non-display fields remain byte-identical to the current Merge.
            output.extend(char.encode('cp1252'))
            continue
        except UnicodeEncodeError:
            pass
        try:
            output.extend(char.encode('cp949'))
        except UnicodeEncodeError as error:
            raise UnicodeEncodeError(
                'cp949/cp1252', text, index, index + 1,
                f'character {char!r} is unavailable in both target encodings',
            ) from error
    return bytes(output)


def decode_field(raw: str) -> str:
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('""', '"')
    return raw


def encode_field(value: str) -> str:
    if any(char in value for char in ('\t', '\r', '\n', '"')):
        return '"' + value.replace('"', '""') + '"'
    return value


@dataclass
class Row:
    fields: list[str]
    newline: str


class TsvDocument:
    """A tolerant TSV reader that preserves every unmodified field verbatim."""

    def __init__(self, text: str):
        self.rows = self._parse(text)

    @staticmethod
    def _parse(text: str) -> list[Row]:
        rows: list[Row] = []
        fields: list[str] = []
        start = 0
        index = 0
        quoted = bool(text) and text[0] == '"'
        if quoted:
            index = 1  # skip the opening quote; keep it in the raw field slice
        while index < len(text):
            char = text[index]
            if quoted:
                if char == '"':
                    if index + 1 < len(text) and text[index + 1] == '"':
                        index += 2
                        continue
                    quoted = False
                index += 1
                continue
            if char == '\t':
                fields.append(text[start:index])
                index += 1
                start = index
                quoted = index < len(text) and text[index] == '"'
                if quoted:
                    index += 1
                continue
            if char in '\r\n':
                fields.append(text[start:index])
                if char == '\r' and index + 1 < len(text) and text[index + 1] == '\n':
                    newline = '\r\n'
                    index += 2
                else:
                    newline = char
                    index += 1
                rows.append(Row(fields, newline))
                fields = []
                start = index
                quoted = index < len(text) and text[index] == '"'
                if quoted:
                    index += 1
                continue
            index += 1
        if start < len(text) or fields:
            fields.append(text[start:])
            rows.append(Row(fields, ''))
        return rows

    def render(self) -> str:
        return ''.join('\t'.join(row.fields) + row.newline for row in self.rows)


def parse_overlay(path: Path) -> dict[tuple[int, str], str]:
    text = path.read_bytes().decode('cp949')
    records: dict[tuple[int, str], str] = {}
    current: tuple[int, str] | None = None
    for line_no, line in enumerate(text.splitlines(), 1):
        parts = line.split('\t', 3)
        if len(parts) >= 4 and parts[1].strip().isdigit():
            key = (int(parts[1].strip()), parts[2].strip())
            records[key] = decode_field(parts[3])
            current = key
        elif current is not None:
            records[current] += '\n' + line
        elif line_no != 1 and line.strip():
            raise ValueError(f'{path.name}:{line_no}: orphan continuation line')
    return records


def find_casefold(folder: Path, name: str) -> Path:
    wanted = name.casefold()
    for candidate in folder.iterdir():
        if candidate.name.casefold() == wanted:
            return candidate
    raise FileNotFoundError(f'{name} was not found in {folder}')


def numeric_rows(doc: TsvDocument, column: int = 0) -> dict[int, Row]:
    result: dict[int, Row] = {}
    for row in doc.rows:
        if len(row.fields) > column:
            value = decode_field(row.fields[column]).strip()
            if value.isdigit():
                result[int(value)] = row
    return result


def apply_direct(
    doc: TsvDocument,
    overlay: dict[tuple[int, str], str],
    column: int,
    *,
    id_column: int = 0,
    id_offset: int = 0,
    overlay_field: str | None = None,
) -> int:
    rows = numeric_rows(doc, id_column)
    changed = 0
    for (record_id, field), value in overlay.items():
        if overlay_field is not None and field != overlay_field:
            continue
        if not value:
            continue
        row = rows.get(record_id + id_offset)
        if row is None:
            raise ValueError(f'missing source row {record_id + id_offset}')
        if len(row.fields) <= column:
            raise ValueError(f'source row {record_id + id_offset} has no column {column}')
        row.fields[column] = encode_field(value)
        changed += 1
    return changed


def apply_by_order(
    doc: TsvDocument,
    overlay: dict[tuple[int, str], str],
    column: int,
    eligible: Callable[[Row, int], bool],
    *,
    overlay_field: str | None = None,
) -> int:
    rows = [row for index, row in enumerate(doc.rows) if eligible(row, index)]
    changed = 0
    for (record_id, field), value in overlay.items():
        if overlay_field is not None and field != overlay_field:
            continue
        if not value:
            continue
        if record_id < 0 or record_id >= len(rows):
            raise ValueError(f'missing source row-order record {record_id}')
        row = rows[record_id]
        if len(row.fields) <= column:
            raise ValueError(f'source row-order record {record_id} has no column {column}')
        row.fields[column] = encode_field(value)
        changed += 1
    return changed


def load_source(source_dir: Path, name: str) -> TsvDocument:
    path = find_casefold(source_dir, name)
    return TsvDocument(path.read_bytes().decode('cp1252'))


def build_npc_greet(source_dir: Path, first: dict[tuple[int, str], str], second: dict[tuple[int, str], str]) -> tuple[TsvDocument, int]:
    """Normalize NPCGreet's legacy unquoted multiline fields without losing metadata."""
    source = find_casefold(source_dir, 'NPCGreet.txt').read_bytes().decode('cp1252')
    chunks = re.split(r'(?m)(?=^\d+\t)', source)
    output = [chunks[0]]
    changed = 0
    for chunk in chunks[1:]:
        id_text, separator, body = chunk.partition('\t')
        if not separator or not id_text.isdigit():
            raise ValueError('could not split an NPCGreet source record')
        record_id = int(id_text)
        greet1 = first.get((record_id, '0'), '')
        greet2 = second.get((record_id, '1'), '')
        if greet1 and greet2:
            # The final three tabs separate Notes, Owner, and the trailing
            # compatibility column even when either greeting contains newlines.
            tail = body.rsplit('\t', 3)
            if len(tail) != 4:
                raise ValueError(f'NPCGreet row {record_id} has no metadata tail')
            newline = '\r\n' if chunk.endswith('\r\n') else ('\n' if chunk.endswith('\n') else '')
            metadata = '\t'.join(tail[1:])
            if newline and not metadata.endswith(newline):
                metadata += newline
            output.append(f'{record_id}\t{encode_field(greet1)}\t{encode_field(greet2)}\t{metadata}')
            changed += 2
        else:
            output.append(chunk)
    return TsvDocument(''.join(output)), changed


def build_multiline_text_table(
    source_dir: Path,
    name: str,
    overlay: dict[tuple[int, str], str],
    *,
    use_row_order: bool = False,
) -> tuple[TsvDocument, int]:
    """Replace a multiline text column while preserving its two metadata columns."""
    source = find_casefold(source_dir, name).read_bytes().decode('cp1252')
    chunks = re.split(r'(?m)(?=^\d+\t)', source)
    output = [chunks[0]]
    changed = 0
    row_order = 0
    for chunk in chunks[1:]:
        id_text, separator, body = chunk.partition('\t')
        if not separator or not id_text.isdigit():
            raise ValueError(f'could not split a {name} source record')
        overlay_id = row_order if use_row_order else int(id_text)
        value = overlay.get((overlay_id, ''), '')
        row_order += 1
        if value:
            tail = body.rsplit('\t', 2)
            if len(tail) > 1:
                output.append(f'{id_text}\t{encode_field(value)}\t' + '\t'.join(tail[1:]))
            else:
                newline = '\r\n' if chunk.endswith('\r\n') else ('\n' if chunk.endswith('\n') else '')
                output.append(f'{id_text}\t{encode_field(value)}{newline}')
            changed += 1
        else:
            output.append(chunk)
    return TsvDocument(''.join(output)), changed


def write_localized(stage_dir: Path, name: str, doc: TsvDocument) -> None:
    plain = encode_mixed_text(doc.render())
    encoded = encode_dbcs_special(plain)
    if decode_dbcs_special(encoded) != plain:
        raise ValueError(f'DBCS round-trip failed for {name}')
    try:
        output = find_casefold(stage_dir, name)
    except FileNotFoundError:
        output = stage_dir / name
    output.write_bytes(encoded)


def apply_map_string_overlays(stage_dir: Path, path: Path) -> dict[str, int]:
    """Replace exact zero-based evt.str entries in selected map STR files."""
    overlays: dict[str, list[tuple[int, str]]] = {}
    for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip() or line.startswith('#') or line.startswith('MapFile\t'):
            continue
        parts = line.split('\t', 2)
        if len(parts) != 3 or not parts[1].strip().isdigit():
            raise ValueError(f'{path.name}:{line_no}: expected MapFile, StringId, Text')
        name, index_text, value = parts
        overlays.setdefault(name.strip(), []).append((int(index_text.strip()), value))

    reports: dict[str, int] = {}
    for name, replacements in overlays.items():
        target = find_casefold(stage_dir, name)
        lines = target.read_bytes().splitlines(keepends=True)
        for index, value in replacements:
            if index < 0 or index >= len(lines):
                raise ValueError(f'{name}: missing evt.str[{index}]')
            current = lines[index]
            newline = b'\r\n' if current.endswith(b'\r\n') else (b'\n' if current.endswith(b'\n') else b'')
            encoded = encode_dbcs_special(encode_mixed_text(value))
            if decode_dbcs_special(encoded) != encode_mixed_text(value):
                raise ValueError(f'DBCS round-trip failed for {name} evt.str[{index}]')
            lines[index] = encoded + newline
        target.write_bytes(b''.join(lines))
        reports[name] = len(replacements)
    return reports


def relative_argument(path: Path, cwd: Path) -> str:
    return str(path.resolve().relative_to(cwd.resolve())) if path.resolve().is_relative_to(cwd.resolve()) else str(Path('..') / Path(*path.resolve().parts[1:]))


def mmarch_path(path: Path, cwd: Path) -> str:
    # mmarch 3.2 misparses drive-colon absolute paths. All build inputs are
    # copied or created on the same drive, so a normal relative path is safe.
    import os
    return os.path.relpath(path.resolve(), cwd.resolve())


def run_mmarch(mmarch: Path, cwd: Path, *args: str) -> None:
    command = [str(mmarch.resolve()), *args]
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"mmarch failed ({result.returncode}): {' '.join(command)}\n{result.stdout}\n{result.stderr}")


def build(args: argparse.Namespace) -> dict[str, int]:
    source_lod = args.source_lod.resolve()
    base_lod = args.base_lod.resolve()
    translations = args.translations.resolve()
    output = args.output.resolve()
    mmarch = args.mmarch.resolve()
    for required in (source_lod, base_lod, translations, mmarch):
        if not required.exists():
            raise FileNotFoundError(required)
    if output.exists() and not args.force:
        raise FileExistsError(f'{output} exists; pass --force to replace it')
    output.parent.mkdir(parents=True, exist_ok=True)

    reports: dict[str, int] = {}
    with tempfile.TemporaryDirectory(prefix='mmmerge-ko-static-', dir=output.parent) as temporary:
        work = Path(temporary)
        source_dir = work / 'source'
        stage_dir = work / 'stage'
        run_mmarch(mmarch, work, 'extract', mmarch_path(source_lod, work), mmarch_path(source_dir, work))
        run_mmarch(mmarch, work, 'extract', mmarch_path(base_lod, work), mmarch_path(stage_dir, work))

        def overlay(name: str) -> dict[tuple[int, str], str]:
            return parse_overlay(translations / name)

        direct_plans = [
            ('Autonote.txt', 'KO_AutonoteTxt.txt', 1, None, 0),
            ('Awards.txt', 'KO_AwardsTxt.txt', 1, None, 0),
            ('Global.TXT', 'KO_GlobalTxt.txt', 1, None, 0),
            ('MapStats.txt', 'KO_MapStats.txt', 1, 'Name', 0),
            ('NPCData.txt', 'KO_NPCData.txt', 1, 'Name', 0),
            ('NPCTopic.txt', 'KO_NPCTopic.txt', 1, None, 0),
            ('Placemon.txt', 'KO_PlaceMonTxt.txt', 1, None, 0),
            ('Quests.txt', 'KO_QuestsTxt.txt', 1, None, 0),
        ]
        for target, source, column, field, offset in direct_plans:
            doc = load_source(source_dir, target)
            reports[target] = apply_direct(doc, overlay(source), column, overlay_field=field, id_offset=offset)
            write_localized(stage_dir, target, doc)

        doc, reports['NPCGreet.txt'] = build_npc_greet(
            source_dir, overlay('KO_NPCGreet1.txt'), overlay('KO_NPCGreet2.txt')
        )
        write_localized(stage_dir, 'NPCGreet.txt', doc)

        doc, reports['NPCText.txt'] = build_multiline_text_table(
            source_dir, 'NPCText.txt', overlay('KO_NPCText.txt')
        )
        write_localized(stage_dir, 'NPCText.txt', doc)

        doc = load_source(source_dir, 'NPCNews.txt')
        news_row = lambda row, index: bool(
            row.fields and re.match(r'^\d+', decode_field(row.fields[0]).strip())
        )
        reports['NPCNews.txt'] = apply_by_order(doc, overlay('KO_NPCNews.txt'), 1, news_row)
        reports['NPCNews.txt'] += apply_by_order(doc, overlay('KO_NPCNewsTopics.txt'), 2, news_row)
        write_localized(stage_dir, 'NPCNews.txt', doc)

        doc = load_source(source_dir, 'class.txt')
        class_row = lambda row, index: index >= 1 and len(row.fields) >= 2 and bool(decode_field(row.fields[0]).strip())
        reports['class.txt'] = apply_by_order(doc, overlay('KO_ClassNames.txt'), 0, class_row)
        reports['class.txt'] += apply_by_order(doc, overlay('KO_ClassDescriptions.txt'), 1, class_row)
        write_localized(stage_dir, 'class.txt', doc)

        doc, reports['scroll.txt'] = build_multiline_text_table(
            source_dir, 'scroll.txt', overlay('KO_MessageScrolls.txt'), use_row_order=True
        )
        write_localized(stage_dir, 'scroll.txt', doc)

        # Game.TransTxt is indexed by row order; the source 2D# column has gaps.
        doc = load_source(source_dir, 'Trans.txt')
        trans_row = lambda row, index: bool(row.fields and decode_field(row.fields[0]).strip().isdigit())
        reports['Trans.txt'] = apply_by_order(doc, overlay('KO_TransTxt.txt'), 1, trans_row)
        write_localized(stage_dir, 'Trans.txt', doc)

        doc = load_source(source_dir, 'SPCITEMS.TXT')
        spc_row = lambda row, index: index >= 4 and len(row.fields) >= 2 and bool(decode_field(row.fields[0]).strip())
        reports['SPCITEMS.TXT'] = apply_by_order(doc, overlay('KO_SpcItemsTxtStats.txt'), 0, spc_row, overlay_field='BonusStat')
        reports['SPCITEMS.TXT'] += apply_by_order(doc, overlay('KO_SpcItemsTxtNames.txt'), 1, spc_row, overlay_field='NameAdd')
        write_localized(stage_dir, 'SPCITEMS.TXT', doc)

        doc = load_source(source_dir, 'STDITEMS.TXT')
        std_row = lambda row, index: index >= 4 and len(row.fields) >= 2 and bool(decode_field(row.fields[0]).strip())
        reports['STDITEMS.TXT'] = apply_by_order(doc, overlay('KO_StdItemsTxtStats.txt'), 0, std_row, overlay_field='BonusStat')
        reports['STDITEMS.TXT'] += apply_by_order(doc, overlay('KO_StdItemsTxtNames.txt'), 1, std_row, overlay_field='NameAdd')
        write_localized(stage_dir, 'STDITEMS.TXT', doc)

        doc = load_source(source_dir, 'Spells.txt')
        spell_columns = {'Name': 2, 'ShortName': 4, 'Description': 5, 'Normal': 6, 'Expert': 7, 'Master': 8, 'GrandMaster': 9}
        reports['Spells.txt'] = 0
        spell_overlay = overlay('KO_SpellsTxt.txt')
        for field, column in spell_columns.items():
            reports['Spells.txt'] += apply_direct(doc, spell_overlay, column, overlay_field=field)
        write_localized(stage_dir, 'Spells.txt', doc)

        reports.update(apply_map_string_overlays(stage_dir, translations / 'KO_MapStrings.txt'))

        # Keep the already-tested compact MM7/MM8 history files from base_lod.
        # The full source translations exceed an engine-side history buffer and
        # make MM8 crash before Lua initialization.

        temporary_output = work / output.name
        run_mmarch(
            mmarch,
            work,
            'create',
            mmarch_path(temporary_output, work),
            'mm8loclod',
            '.',
            mmarch_path(stage_dir, work) + '\\*',
        )
        if not temporary_output.exists() or temporary_output.stat().st_size == 0:
            raise RuntimeError('mmarch did not create a non-empty archive')
        archive_list = subprocess.run(
            [str(mmarch), 'list', mmarch_path(temporary_output, work), '\n'],
            cwd=work, text=True, capture_output=True, check=True,
        ).stdout.casefold()
        for required_name in reports:
            if required_name.casefold() not in archive_list:
                raise RuntimeError(f'{required_name} is missing from the built archive')
        if output.exists():
            output.unlink()
        shutil.move(str(temporary_output), str(output))
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-lod', type=Path, required=True, help='current game Data/mmmerge.T.lod')
    parser.add_argument('--base-lod', type=Path, required=True, help='existing Korean LOD with fonts and STR files')
    parser.add_argument('--translations', type=Path, required=True, help='folder containing KO_*.txt files')
    parser.add_argument('--mmarch', type=Path, required=True, help='mmarch.exe path')
    parser.add_argument('--output', type=Path, required=True, help='output test LOD')
    parser.add_argument('--force', action='store_true', help='replace an existing output file')
    args = parser.parse_args()
    reports = build(args)
    print(f'Built {args.output.resolve()}')
    for name, count in sorted(reports.items(), key=lambda item: item[0].casefold()):
        print(f'{name}: {count} localized records')


if __name__ == '__main__':
    main()
