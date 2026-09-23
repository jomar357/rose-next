"""Resolve DLGINFO's atlas references and render an art-only diagnostic preview.

Not a game screenshot: gauges are fully filled; dynamic text, status icons,
conditional visibility, native font rendering and input are not simulated.
Requires Pillow. Reads donor files only, outputs under --output.
"""
import argparse
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--client', type=Path, default=Path(r'C:\Users\Thomas\Desktop\Testclients\667'))
    p.add_argument('--output', type=Path, default=Path('build/667-ui-audit/hud-assets'))
    args = p.parse_args()
    xml_dir = args.client / '3Ddata/Control/Xml'
    res = args.client / 'extracted data/3DDATA/CONTROL/RES'
    data = (res / 'UI2.TSI').read_bytes()
    n = struct.unpack_from('<h', data)[0]
    pos, textures, sprites = 2, [], []
    for _ in range(n):
        size = struct.unpack_from('<h', data, pos)[0]
        pos += 2
        textures.append(data[pos:pos+size].rstrip(b'\0').decode('ascii'))
        pos += size + 4
    total = struct.unpack_from('<h', data, pos)[0]
    pos += 2
    for _ in range(n):
        count = struct.unpack_from('<h', data, pos)[0]
        pos += 2
        for _ in range(count):
            tex, x1, y1, x2, y2, color, name = struct.unpack_from('<h4iI32s', data, pos)
            pos += 54
            sprites.append({'texture': textures[tex], 'rect': [x1, y1, x2, y2],
                            'tsi_name': name.rstrip(b'\0').decode('ascii')})
    if pos != len(data) or total != len(sprites):
        raise ValueError('Unexpected atlas layout')
    ids = {}
    for line in (xml_dir / 'UI2_strID.ID').read_text().splitlines():
        fields = line.split()
        if len(fields) == 2:
            ids[fields[0]] = int(fields[1])
    root = ET.fromstring((xml_dir / 'DLGINFO.XML').read_bytes())
    canvas = Image.new('RGBA', (330, 125))
    sheets, references, controls = {}, {}, []

    def sprite(name):
        index = ids[name]
        record = sprites[index]
        references[name] = {'index': index, **record}
        texture = record['texture']
        if texture not in sheets:
            sheets[texture] = Image.open(res / texture).convert('RGBA')
        x1, y1, x2, y2 = record['rect']
        sheet = sheets[texture]
        if not (0 <= x1 < x2 <= sheet.width and 0 <= y1 < y2 <= sheet.height):
            raise ValueError(f'Out-of-bounds sprite: {name}')
        return sheet.crop((x1, y1, x2, y2))

    for node in root.iter():
        if node.get('NAME'):
            controls.append({'tag': node.tag, **node.attrib})
        if node.tag not in ('IMAGE', 'GUAGE'):
            continue
        x = int(node.get('X', 0)) + int(node.get('OFFSETX', 0))
        y = int(node.get('Y', 0)) + int(node.get('OFFSETY', 0))
        for field in (('BGID', 'GID') if node.tag == 'GUAGE' else ('GID',)):
            name = node.get(field, '')
            if not name:
                continue
            if node.get('MODULEID') != '11':
                raise ValueError(f'Unexpected module: {node.attrib}')
            art = sprite(name)
            if node.get('SIZEFIT') == '1':
                art = art.resize((int(node.get('WIDTH')), int(node.get('HEIGHT'))), Image.Resampling.BILINEAR)
            canvas.alpha_composite(art, (x, y))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'hud-assets.json').write_text(json.dumps({
        'root': root.attrib, 'named_controls': controls, 'sprites': references,
        'limitations': __doc__,
    }, indent=2), encoding='utf-8')
    canvas.save(args.output / 'hud-art.png')
    preview = Image.new('RGB', (1060, 480), '#222731')
    draw = ImageDraw.Draw(preview)
    draw.text((24, 18), '667 avatar HUD: static artwork reconstruction (3x)', fill='white')
    enlarged = canvas.resize((990, 375), Image.Resampling.NEAREST)
    preview.paste(enlarged, (24, 55), enlarged)
    draw.text((24, 440), 'Full gauges. No dynamic text/status icons. Right-side gauges shown regardless of runtime visibility.', fill='#c6ccd7')
    preview.save(args.output / 'hud-art-preview.png')
    print(f'{len(references)} sprite names resolved; {len(controls)} named controls; output: {args.output}')


if __name__ == '__main__':
    main()
