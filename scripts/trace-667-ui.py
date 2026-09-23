"""Static x86 control-flow traces for the 667 avatar-info investigation.

Read-only inputs. Requires pefile/capstone. Addresses and labels target the hashes
recorded in doc/667UI/667-ui-investigation.md. Indirect branches are reported unresolved
except for manually verified, hash-specific switch tables. Direct calls are annotated,
not recursively executed or followed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import capstone as cs
import pefile


SEEDS = {
    0x5278e0: 'CAvatarInfoDlg_Create',
    0x527910: 'CAvatarInfoDlg_MoveWindow_POINT',
    0x527990: 'CAvatarInfoDlg_observer_Update_candidate',
    0x527ef0: 'CAvatarInfoDlg_RefreshDlg',
    0x528310: 'CAvatarInfoDlg_destructor_adjustor',
    0x528a20: 'CAvatarInfoDlg_Process',
    0x528f10: 'CAvatarInfoDlg_Update_POINT',
    0x528440: 'CAvatarInfoDlg_Draw',
    0x528dd0: 'CAvatarInfoDlg_Show',
    0x5289f0: 'CAvatarInfoDlg_SetInterfacePos_After_candidate',
    0x5281a0: 'CAvatarInfoDlg_layout_helper',
    0x528870: 'CAvatarInfoDlg_SetMaxView_candidate',
    0x528950: 'CAvatarInfoDlg_SetMinView_candidate',
    0x41d2f0: 'self_target_candidate',
    0x4baad0: 'avatar_HP_percent_helper',
    0x4bac60: 'avatar_MP_percent_helper',
}
EXPECTED = {'TRose.exe': '21802bf965fdca1fd475d6c5fe9025ba8b28c0cdcf388b58ff34090610f00e52',
            'TGameCtrl_r.dll': '2158f01f52f2807c5b4623f30fc2cd494549108c0b3de1c2449470b764afa583'}


class Binary:
    def __init__(self, path):
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != EXPECTED[path.name]:
            raise ValueError('Different binary: addresses must be re-established')
        self.pe = pefile.PE(data=raw)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.sections = [(self.base+s.VirtualAddress,
                          self.base+s.VirtualAddress+s.Misc_VirtualSize, s)
                         for s in self.pe.sections]
        self.names = {x.address: (x.name or b'ordinal').decode()
                      for d in getattr(self.pe, 'DIRECTORY_ENTRY_IMPORT', []) for x in d.imports}
        self.names.update({self.base+x.address: (x.name or b'ordinal').decode()
                           for x in getattr(getattr(self.pe, 'DIRECTORY_ENTRY_EXPORT', None), 'symbols', [])})
        self.md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
        self.md.detail = True

    def data(self, va, size):
        if not any(lo <= va < hi for lo, hi, _ in self.sections):
            return b''
        return self.pe.get_data(va-self.base, size)

    def code(self, va):
        return any(lo <= va < hi and s.Characteristics & 0x20000000
                   for lo, hi, s in self.sections)

    def describe(self, va):
        if va in self.names:
            return self.names[va]
        raw = self.data(va, 128)
        if self.code(va):
            if raw[:2] == b'\xff\x25':
                return self.names.get(struct.unpack_from('<I', raw, 2)[0], '')
            return ''
        raw = raw.split(b'\0')[0]
        if 2 <= len(raw) < 128 and all(32 <= x < 127 for x in raw):
            return repr(raw.decode())
        return ''

    def trace(self, entry, limit=12000):
        pending, decoded, unresolved = [entry], {}, []
        while pending:
            va = pending.pop()
            while va not in decoded:
                if not self.code(va):
                    unresolved.append(f'non-code target {va:#x}')
                    break
                if len(decoded) >= limit:
                    raise ValueError(f'instruction limit at {entry:#x}')
                ins = next(self.md.disasm(self.data(va, 15), va, count=1), None)
                if ins is None:
                    unresolved.append(f'decode failed {va:#x}')
                    break
                decoded[va] = ins
                if ins.group(cs.CS_GRP_RET) or ins.mnemonic in ('int3', 'ud2'):
                    break
                if ins.group(cs.CS_GRP_JUMP):
                    if ins.operands[0].type == cs.x86.X86_OP_IMM:
                        target = ins.operands[0].imm
                        # Named function tailcalls are boundaries.
                        if target not in self.names:
                            pending.append(target)
                    else:
                        # Manually verified cmp ecx,3 / ja default immediately
                        # precedes this four-entry Process switch in this hash.
                        if self.base == 0x400000 and va == 0x528b71:
                            pending.extend(struct.unpack('<4I', self.data(0x528db4, 16)))
                        # Font-face selector checks an unsigned locale index <= 5.
                        elif self.base == 0x400000 and va == 0x49578c:
                            pending.extend(struct.unpack('<6I', self.data(0x495884, 24)))
                        # CTButton::Process subtracts WM_LBUTTONDOWN and checks
                        # the unsigned index <= 4 before this five-entry table.
                        elif self.base == 0x66000000 and va == 0x6602283f:
                            pending.extend(struct.unpack('<5I', self.data(0x660228d4, 20)))
                        else:
                            unresolved.append(f'indirect branch {va:#x}: {ins.op_str}')
                    if ins.mnemonic == 'jmp':
                        break
                va += ins.size
        lines, calls = [], []
        for va, ins in sorted(decoded.items()):
            annotations = []
            for op in ins.operands:
                target = None
                if op.type == cs.x86.X86_OP_IMM:
                    target = op.imm & 0xffffffff
                elif op.type == cs.x86.X86_OP_MEM and not op.mem.base and not op.mem.index:
                    target = op.mem.disp & 0xffffffff
                if target is not None:
                    desc = self.describe(target)
                    if desc:
                        annotations.append(desc)
            if ins.group(cs.CS_GRP_CALL):
                calls.append({'va': hex(va), 'operand': ins.op_str, 'annotation': annotations})
            line = f'{va:08x}  {ins.mnemonic:9} {ins.op_str}'
            if annotations:
                line += ' ; ' + ' | '.join(annotations)
            lines.append(line)
        return '\n'.join(lines), {'entry': hex(entry), 'instructions': len(decoded),
                                   'unresolved': unresolved, 'calls': calls}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--client', type=Path, default=Path(r'C:\Users\Thomas\Desktop\Testclients\667'))
    p.add_argument('--binary', choices=list(EXPECTED), default='TRose.exe')
    p.add_argument('--entry', action='append', help='hex-address:label; replaces default seeds')
    p.add_argument('--output', type=Path, default=Path('build/667-ui-audit/avatar-info'))
    args = p.parse_args()
    seeds = {int(s.split(':', 1)[0], 16): s.split(':', 1)[1] for s in args.entry} if args.entry else SEEDS
    if args.binary != 'TRose.exe' and not args.entry:
        p.error('--entry is required for DLL tracing')
    binary = Binary(args.client / args.binary)
    args.output.mkdir(parents=True, exist_ok=True)
    summaries = {}
    for entry, name in seeds.items():
        assembly, summary = binary.trace(entry)
        (args.output / (name+'.asm.txt')).write_text(assembly+'\n', encoding='utf-8')
        summaries[name] = summary
    (args.output / 'trace-index.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    print(json.dumps({k: {x:v[x] for x in ('entry', 'instructions', 'unresolved')}
                      for k,v in summaries.items()}, indent=2))


if __name__ == '__main__':
    main()
