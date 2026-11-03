"""Draws the integration's icon: a spin bike from the side with a Bluetooth badge.

    python3 assets/make_icons.py   # writes icon.svg, dark_icon.svg and the brand PNGs

Needs rsvg-convert (brew install librsvg).
"""
import pathlib
import subprocess

HERE = pathlib.Path(__file__).parent
BRAND = HERE.parent / 'custom_components' / 'ftms_bike' / 'brand'


def line(x0, y0, x1, y1, width):
    return (f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke-width="{width}" '
            f'stroke-linecap="round"/>')


def svg(frame, wheel, accent):
    cx, cy, rb, gap = 388, 388, 104, 18
    h, w = 120, 60
    corners = [(-w / 2, -h / 4), (w / 2, h / 4), (0, h / 2),
               (0, -h / 2), (w / 2, -h / 4), (-w / 2, h / 4)]
    rune = ' '.join(f'{cx + dx:.1f},{cy + dy:.1f}' for dx, dy in corners)
    # Facing left: flywheel at the front under the bars, saddle at the back, the badge
    # where the rear foot would be. It cuts a transparent ring out of the bike, so it
    # reads on any background.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <mask id="cut">
    <rect width="512" height="512" fill="#fff"/>
    <circle cx="{cx}" cy="{cy}" r="{rb + gap}" fill="#000"/>
  </mask>
  <g mask="url(#cut)">
    <g stroke="{frame}" fill="none">
      {line(46, 462, 250, 462, 34)}
      {line(150, 300, 150, 462, 34)}
      {line(150, 300, 296, 316, 40)}
      {line(178, 286, 150, 92, 36)}
      {line(86, 84, 206, 84, 32)}
      {line(296, 316, 336, 150, 34)}
      {line(292, 134, 420, 134, 38)}
    </g>
    <circle cx="150" cy="300" r="112" fill="{wheel}" stroke="{frame}" stroke-width="22"/>
    <circle cx="150" cy="300" r="78" fill="none" stroke="{accent}" stroke-width="14"/>
    <circle cx="150" cy="300" r="26" fill="{frame}"/>
    <circle cx="296" cy="316" r="34" fill="{wheel}" stroke="{frame}" stroke-width="14"/>
  </g>
  <circle cx="{cx}" cy="{cy}" r="{rb}" fill="#1E88E5"/>
  <polyline points="{rune}" fill="none" stroke="#FFFFFF" stroke-width="18"
            stroke-linecap="round" stroke-linejoin="round"/>
</svg>
'''


VARIANTS = {
    '': svg(frame='#37474F', wheel='#263238', accent='#FFC107'),
    'dark_': svg(frame='#B0BEC5', wheel='#78909C', accent='#FFD54F'),
}
BRAND.mkdir(exist_ok=True)
for prefix, text in VARIANTS.items():
    source = HERE / f'{prefix}icon.svg'
    source.write_text(text)
    for suffix, size in (('', 256), ('@2x', 512)):
        subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size), '-o',
                        BRAND / f'{prefix}icon{suffix}.png', source], check=True)
print('wrote', sorted(p.name for p in BRAND.iterdir()))
