"""Build assets/social-preview.png, the repo's social preview (1280x640).

Needs Pillow, the Charis SIL font and the CookLLM logo:

    python3 assets/make-preview.py <charis.woff2> <logo.png> [title]
"""

import sys
from PIL import Image, ImageDraw, ImageFont
FONT, LOGO = sys.argv[1], sys.argv[2]
title = sys.argv[3] if len(sys.argv) > 3 else 'AI PhD Internships'
W, H = 1280, 640
bg, fg, muted, green = '#faf9f5', '#141413', '#6b6a64', '#1d6e47'
im = Image.new('RGB', (W, H), bg)
d = ImageDraw.Draw(im)
d.rectangle([96, 162, 104, 368], fill=green)
d.text((136, 140), title, font=ImageFont.truetype(FONT, 92), fill=fg)
d.text((140, 262), 'Research internships that ask for a PhD,', font=ImageFont.truetype(FONT, 40), fill=muted)
d.text((140, 314), 'from company careers pages. Updated daily.', font=ImageFont.truetype(FONT, 40), fill=muted)
areas = 'LLMs, vision, robotics, systems, AI for science, quant research'
d.text((140, 420), areas, font=ImageFont.truetype(FONT, 30), fill=green)
logo = Image.open(LOGO).convert('RGBA')
logo.thumbnail((56, 56))
im.paste(logo, (140, 520), logo)
d.text((140 + logo.width + 18, 528), 'CookLLM', font=ImageFont.truetype(FONT, 36), fill=fg)
im.save('assets/social-preview.png', optimize=True)
print(im.size)
