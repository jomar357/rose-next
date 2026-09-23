"""Read-only 667 UI reconnaissance; writes evidence only to --output.

Requires pefile and capstone. No client launch, asset import, or game edits.
XML comparisons are structural leads, NOT proof of C++ compatibility: IDs can
repeat in different panes, and controls/slots can be created entirely in code.
Addresses are preferred-image VAs (relocate them for a running process).
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

import capstone
import pefile


def xml_inventory(folder):
    result = {}
    for path in sorted(folder.glob('*.xml')):
        raw = path.read_bytes()
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            result[path.name.lower()] = {'error': str(exc)}
            continue
        nodes = []

        def visit(node, parent):
            key = parent + '/' + node.tag + '[' + node.get('ID', '') + ']'
            nodes.append({'path': key, 'tag': node.tag, **node.attrib})
            for child in node:
                visit(child, key)

        visit(root, '')
        result[path.name.lower()] = {
            'sha256': hashlib.sha256(raw).hexdigest(),
            'root': root.attrib, 'nodes': nodes,
        }
    return result


def compare(ours, donor):
    rows = []
    for name in sorted(ours.keys() & donor.keys()):
        a, b = ours[name], donor[name]
        if 'error' in a or 'error' in b:
            continue

        def signatures(doc):
            ids = collections.defaultdict(set)
            for node in doc['nodes']:
                if node.get('ID', '0') != '0' and 'ID' in node:
                    ids[node['ID']].add(node['tag'])
            return ids

        x, y = signatures(a), signatures(b)
        rows.append({
            'file': name, 'byte_identical': a['sha256'] == b['sha256'],
            'ours_size': [a['root'].get(k) for k in ('WIDTH', 'HEIGHT')],
            'donor_size': [b['root'].get(k) for k in ('WIDTH', 'HEIGHT')],
            'missing_ids': sorted(x.keys() - y.keys()),
            'added_ids': sorted(y.keys() - x.keys()),
            'changed_id_tags': {k: [sorted(x[k]), sorted(y[k])]
                                for k in sorted(x.keys() & y.keys()) if x[k] != y[k]},
        })
    return rows


def atlas_inventory(path):
    data = path.read_bytes()
    count = struct.unpack_from('<h', data)[0]
    pos, textures = 2, []
    for _ in range(count):
        length = struct.unpack_from('<h', data, pos)[0]
        pos += 2
        name = data[pos:pos+length].rstrip(b'\0').decode('ascii')
        pos += length + 4
        textures.append({'name': name, 'exists': (path.parent / name).is_file()})
    declared = struct.unpack_from('<h', data, pos)[0]
    pos += 2
    for texture in textures:
        sprites = struct.unpack_from('<h', data, pos)[0]
        pos += 2 + 54 * sprites
        texture['sprites'] = sprites
    if pos != len(data):
        raise ValueError(f'{path}: unexpected TSI size/layout ({pos} != {len(data)})')
    return {'textures': textures, 'declared_sprites': declared,
            'actual_sprites': sum(t['sprites'] for t in textures)}


def binary_inventory(path, out):
    raw = path.read_bytes()
    pe = pefile.PE(data=raw)
    base = pe.OPTIONAL_HEADER.ImageBase
    exports = [{'name': (s.name or b'').decode('ascii', 'replace'),
                'ordinal': s.ordinal, 'va': hex(base + s.address)}
               for s in getattr(getattr(pe, 'DIRECTORY_ENTRY_EXPORT', None), 'symbols', [])]
    imports = {entry.dll.decode(): [
        {'name': (item.name or b'').decode('ascii', 'replace'),
         'ordinal': item.ordinal, 'iat_va': hex(item.address)}
        for item in entry.imports]
        for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])}
    strings = []
    for match in re.finditer(rb'[ -~]{5,}', raw):
        value = match.group().decode('ascii')
        if (value.startswith('.?AV') or 'control\\' in value.lower()
                or '.pdb' in value.lower() or re.fullmatch(r'Dlg\w+', value)):
            strings.append({'offset': hex(match.start()),
                            'va': hex(base + pe.get_rva_from_offset(match.start())),
                            'value': value})
    # Linear decoding is a discovery aid; it does not establish function bounds.
    # Only calls through named TGameCtrl IAT entries are retained.
    iat = {int(x['iat_va'], 16): x['name']
           for dll, entries in imports.items() if dll.lower() == 'tgamectrl_r.dll'
           for x in entries}
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.skipdata = True
    calls = []
    for section in pe.sections:
        if not section.Characteristics & 0x20000000:
            continue
        for address, size, mnemonic, operands in md.disasm_lite(
                section.get_data(), base + section.VirtualAddress):
            if mnemonic not in ('call', 'jmp'):
                continue
            match = re.fullmatch(r'dword ptr \[(0x[0-9a-f]+)\]', operands)
            if match and int(match[1], 16) in iat:
                calls.append({'va': hex(address), 'instruction': mnemonic,
                              'target': iat[int(match[1], 16)]})
    selected = ('MakeDialogByXML@', 'Find@CTDialog@', 'GetControlName@',
                'RefreshDlg@', 'SetInterfacePos_After@', 'Draw@CTImage@')
    md.skipdata = False
    snippets = []
    for symbol in exports:
        if not any(key in symbol['name'] for key in selected):
            continue
        va = int(symbol['va'], 16)
        snippets.append('\n' + symbol['name'] + ' at ' + symbol['va'])
        # Bounded preview only; do not treat the next export as a function end.
        for address, size, mnemonic, operands in md.disasm_lite(pe.get_data(va-base, 512), va):
            snippets.append(f'{address:08x}  {mnemonic:8} {operands}')
            if mnemonic.startswith('ret'):
                break
    (out / (path.name + '.asm.txt')).write_text('\n'.join(snippets), encoding='utf-8')
    # MSVC x86 RTTI: type descriptor -> complete object locator -> vtable.
    # Keep secondary tables separate and stop at the first non-code pointer.
    executable = [(base+s.VirtualAddress, base+s.VirtualAddress+s.Misc_VirtualSize)
                  for s in pe.sections if s.Characteristics & 0x20000000]
    def is_code(va):
        return any(lo <= va < hi for lo, hi in executable)
    tables = []
    for class_name in ('CItemDlg', 'CAvatarInfoDlg', 'CChatDLG'):
        offset = raw.find(('.?AV'+class_name+'@@').encode())
        if offset < 0:
            continue
        type_va = base + pe.get_rva_from_offset(offset) - 8
        locators = []
        for section in pe.sections:
            data = section.get_data()
            for pos in range(0, len(data)-19, 4):
                sig, suboffset, cd, typ, hierarchy = struct.unpack_from('<5I', data, pos)
                if sig == 0 and typ == type_va and suboffset < 4096:
                    locators.append((base+section.VirtualAddress+pos, suboffset))
        for locator, suboffset in locators:
            for section in pe.sections:
                data = section.get_data()
                for pos in range(0, len(data)-7, 4):
                    if struct.unpack_from('<I', data, pos)[0] != locator:
                        continue
                    entries = []
                    for at in range(pos+4, min(len(data)-3, pos+4+4*128), 4):
                        va = struct.unpack_from('<I', data, at)[0]
                        if not is_code(va):
                            break
                        entries.append(hex(va))
                    if entries:
                        named_thunks = {}
                        for index, entry in enumerate(entries):
                            code = pe.get_data(int(entry, 16)-base, 6)
                            if code[:2] == b'\xff\x25':
                                target = struct.unpack_from('<I', code, 2)[0]
                                if target in iat:
                                    named_thunks[str(index)] = iat[target]
                        tables.append({'class': class_name, 'type_descriptor': hex(type_va),
                                       'locator': hex(locator), 'subobject_offset': suboffset,
                                       'vtable': hex(base+section.VirtualAddress+pos+4),
                                       'entries': entries, 'named_import_thunks': named_thunks})
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'image_base': hex(base),
            'machine': hex(pe.FILE_HEADER.Machine), 'exports': exports,
            'imports': imports, 'strings': strings, 'ui_import_calls': calls,
            'rtti_vtable_candidates': tables,
            'sections': [{'name': s.Name.rstrip(b'\0').decode(),
                          'rva': hex(s.VirtualAddress), 'raw_size': s.SizeOfRawData}
                         for s in pe.sections]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path,
                        default=Path(r'C:\Users\Thomas\Desktop\Testclients\667'))
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, default=Path('build/667-ui-audit'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    donor = xml_inventory(args.client / '3Ddata/Control/Xml')
    ours = xml_inventory(args.repo / 'data/3DDATA/CONTROL/xml')
    dormant = xml_inventory(args.repo / 'data/3DDATA/CONTROL/XMLNEW')
    report = {'donor_xml': donor, 'ours_xml': ours,
              'ui2_atlas': atlas_inventory(args.client / 'extracted data/3DDATA/CONTROL/RES/UI2.TSI'),
              'comparisons': compare(ours, donor),
              'dormant_comparisons': compare(dormant, donor),
              'donor_only_xml': sorted(donor.keys() - ours.keys()),
              'ours_only_xml': sorted(ours.keys() - donor.keys()),
              'binaries': {name: binary_inventory(args.client / name, args.output)
                           for name in ('TRose.exe', 'TGameCtrl_r.dll')}}
    (args.output / 'audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    summary = {'xml_counts': {'donor': len(donor), 'ours': len(ours), 'dormant': len(dormant)},
               'shared_xml': len(report['comparisons']),
               'files_with_missing_ids': sum(bool(x['missing_ids']) for x in report['comparisons']),
               'files_with_changed_id_tags': sum(bool(x['changed_id_tags']) for x in report['comparisons']),
               'parse_errors': {label: {k: v['error'] for k, v in docs.items() if 'error' in v}
                                for label, docs in [('donor', donor), ('ours', ours), ('dormant', dormant)]},
               'binary_counts': {name: {'exports': len(b['exports']),
                                       'ui_import_calls': len(b['ui_import_calls'])}
                                 for name, b in report['binaries'].items()}}
    print(json.dumps(summary, indent=2))
    print('Evidence:', args.output.resolve())


if __name__ == '__main__':
    main()
