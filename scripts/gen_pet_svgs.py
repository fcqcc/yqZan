#!/usr/bin/env python3
"""生成所有宠物 SVG 图片"""
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "pets")

# ===== 每只宠物的基础色板 =====
PALETTES = {
    "pig": {
        "baby":   {"body": "#FFB5C5", "accent": "#FF8FA3", "eye": "#5C3D4A", "outline": "#D4748A"},
        "teen":   {"body": "#FF9AB5", "accent": "#FF7A9E", "eye": "#5C3D4A", "outline": "#D0607A"},
        "adult":  {"body": "#FF8099", "accent": "#FF607F", "eye": "#4A2E3A", "outline": "#C44D6A"},
        "deluxe": {"body": "#FFD700", "accent": "#FFA500", "eye": "#5C3D10", "outline": "#B8860B"},
        "legend": {"body": "#FF69B4", "accent": "#FF1493", "eye": "#3D1A2A", "outline": "#C71585",
                   "crown": "#FFD700", "glow": "#FFB6C1"},
    },
    "fox": {
        "baby":   {"body": "#FFB347", "accent": "#FFF5E0", "eye": "#4A3520", "outline": "#D4903A"},
        "teen":   {"body": "#FF8C00", "accent": "#FFE4B5", "eye": "#4A3520", "outline": "#CC7000"},
        "adult":  {"body": "#FF6600", "accent": "#FFD19A", "eye": "#3D2A15", "outline": "#B84E00"},
        "deluxe": {"body": "#C0C0C0", "accent": "#E8E8E8", "eye": "#2A2A3D", "outline": "#8A8A8A",
                   "moon": "#FFFACD"},
        "legend": {"body": "#1A1A4E", "accent": "#4A4A8A", "eye": "#FFFFFF", "outline": "#6A6AAA",
                   "stars": "#FFD700"},
    },
    "cat": {
        "baby":   {"body": "#FFE4E1", "accent": "#FFB6C1", "eye": "#4A6A4A", "outline": "#D4A0A0"},
        "teen":   {"body": "#FFD4C0", "accent": "#FFA07A", "eye": "#3D5C3D", "outline": "#CC8866"},
        "adult":  {"body": "#FFAB76", "accent": "#FF7F50", "eye": "#3D4A2A", "outline": "#B86A3A"},
        "deluxe": {"body": "#FF6347", "accent": "#FFD700", "eye": "#3D2A1A", "outline": "#B84A30",
                   "bell": "#FFD700"},
        "legend": {"body": "#708090", "accent": "#C0C0C0", "eye": "#FF4500", "outline": "#4A505A",
                   "gear": "#FFD700"},
    },
    "unicorn": {
        "baby":   {"body": "#FFF0F5", "accent": "#FFB6C1", "eye": "#6A4A6A", "outline": "#D4A0C0",
                   "horn": "#FFD700"},
        "teen":   {"body": "#FFE4F0", "accent": "#FF69B4", "eye": "#5A3D5A", "outline": "#CC80A0",
                   "horn": "#FFD700", "rainbow": "#FF0000"},
        "adult":  {"body": "#E8D4F0", "accent": "#DA70D6", "eye": "#4A2A5A", "outline": "#A860B0",
                   "horn": "#FFD700"},
        "deluxe": {"body": "#C0B0E0", "accent": "#9370DB", "eye": "#3D1A4A", "outline": "#8050A0",
                   "horn": "#FFFACD", "glow": "#E8D0F0"},
        "legend": {"body": "#FFFFFF", "accent": "#FFD700", "eye": "#2A1A3D", "outline": "#C0A0D0",
                   "horn": "#FFD700", "glow": "#FFFACD", "stars": "#FFD700"},
    },
    "dragon": {
        "baby":   {"body": "#90EE90", "accent": "#32CD32", "eye": "#2A4A2A", "outline": "#5A9A5A"},
        "teen":   {"body": "#66CDAA", "accent": "#20B2AA", "eye": "#2A3D2A", "outline": "#3D8A6A"},
        "adult":  {"body": "#4169E1", "accent": "#1E90FF", "eye": "#1A2A4A", "outline": "#2A5090"},
        "deluxe": {"body": "#FFD700", "accent": "#FFA500", "eye": "#4A2A0A", "outline": "#B8860B",
                   "crown": "#FF4500"},
        "legend": {"body": "#8B0000", "accent": "#FF4500", "eye": "#FFD700", "outline": "#CC0000",
                   "glow": "#FF4500", "flame": "#FFD700"},
    },
}

# ===== SVG 模板函数 =====

def svg_base(content, bg="none", w=200, h=200):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <rect width="{w}" height="{h}" fill="{bg}" rx="20"/>
  {content}
</svg>'''

def pig_svg(p):
    c = PALETTES["pig"][p]
    body = f'''<ellipse cx="100" cy="110" rx="65" ry="55" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>
      <ellipse cx="70" cy="75" rx="18" ry="14" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="2"/>
      <ellipse cx="130" cy="75" rx="18" ry="14" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="2"/>'''
    face = f'''<ellipse cx="100" cy="125" rx="22" ry="16" fill="{c["accent"]}" stroke="{c["outline"]}" stroke-width="2"/>
      <circle cx="85" cy="120" r="4" fill="{c["eye"]}"/>
      <circle cx="115" cy="120" r="4" fill="{c["eye"]}"/>
      <ellipse cx="100" cy="133" rx="5" ry="3" fill="{c["outline"]}"/>'''
    # 鼻孔
    nose = f'''<circle cx="96" cy="128" r="2" fill="{c["outline"]}"/><circle cx="104" cy="128" r="2" fill="{c["outline"]}"/>'''
    extra = ""
    if p == "deluxe":
        extra = f'''<text x="100" y="40" font-size="20" text-anchor="middle">👑</text>'''
    elif p == "legend":
        extra = f'''<text x="100" y="35" font-size="22" text-anchor="middle">✨</text>
          <ellipse cx="100" cy="110" rx="70" ry="60" fill="none" stroke="{c["glow"]}" stroke-width="4" opacity="0.5"/>'''
    return svg_base(body + face + nose + extra)


def fox_svg(p):
    c = PALETTES["fox"][p]
    # 尖耳朵 + 圆脸
    ears = f'''<polygon points="55,80 45,30 80,70" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>
      <polygon points="145,80 155,30 120,70" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>
      <polygon points="55,75 48,38 75,68" fill="{c["accent"]}"/>
      <polygon points="145,75 152,38 125,68" fill="{c["accent"]}"/>'''
    body = f'''<ellipse cx="100" cy="115" rx="55" ry="50" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>'''
    face = f'''<ellipse cx="100" cy="120" rx="18" ry="14" fill="{c["accent"]}" stroke="{c["outline"]}" stroke-width="2"/>
      <circle cx="88" cy="115" r="4" fill="{c["eye"]}"/>
      <circle cx="112" cy="115" r="4" fill="{c["eye"]}"/>
      <text x="100" y="132" font-size="10" text-anchor="middle" fill="{c["outline"]}">▼</text>'''
    extra = ""
    if p == "deluxe":
        extra = f'''<circle cx="100" cy="35" r="15" fill="{c["moon"]}" stroke="{c["outline"]}" stroke-width="2"/>
          <text x="100" y="40" font-size="12" text-anchor="middle" fill="{c["outline"]}">🌙</text>'''
    elif p == "legend":
        extra = f'''<rect x="40" y="20" width="120" height="15" rx="7" fill="#1A1A4E"/>
          <text x="100" y="33" font-size="10" text-anchor="middle" fill="{c["stars"]}">✦ ✦ ✦</text>'''
    return svg_base(ears + body + face + extra)


def cat_svg(p):
    c = PALETTES["cat"][p]
    ears = f'''<polygon points="50,85 40,25 75,75" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>
      <polygon points="150,85 160,25 125,75" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>
      <polygon points="52,80 44,32 72,72" fill="{c["accent"]}"/>
      <polygon points="148,80 156,32 128,72" fill="{c["accent"]}"/>'''
    body = f'''<ellipse cx="100" cy="110" rx="50" ry="45" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>'''
    face = f'''<circle cx="85" cy="108" r="5" fill="{c["eye"]}"/>
      <circle cx="115" cy="108" r="5" fill="{c["eye"]}"/>
      <circle cx="88" cy="105" r="1.5" fill="white"/>
      <circle cx="118" cy="105" r="1.5" fill="white"/>
      <ellipse cx="100" cy="118" rx="5" ry="3" fill={'"#FFB6C1"' if p == "baby" else f'"{c["accent"]}"'} />
      <text x="100" y="128" font-size="18" text-anchor="middle" fill="{c["outline"]}" opacity="0.3">⬡</text>'''
    extra = ""
    if p == "deluxe":
        extra = f'''<circle cx="100" cy="30" r="10" fill="{c["bell"]}" stroke="#B8860B" stroke-width="2"/>
          <circle cx="100" cy="30" r="3" fill="#B8860B"/>'''
    elif p == "legend":
        extra = f'''<circle cx="160" cy="30" r="12" fill="{c["gear"]}" stroke="#8A6A00" stroke-width="2"/>
          <text x="160" y="35" font-size="14" text-anchor="middle" fill="#8A6A00">⚙</text>'''
    return svg_base(ears + body + face + extra)


def unicorn_svg(p):
    c = PALETTES["unicorn"][p]
    # 马脸 + 喇叭
    horn = f'''<polygon points="100,15 92,50 108,50" fill="{c["horn"]}" stroke="#B8860B" stroke-width="2"/>'''
    head = f'''<ellipse cx="100" cy="80" rx="35" ry="32" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>
      <ellipse cx="100" cy="110" rx="45" ry="55" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>'''
    mane = f'''<path d="M65 65 Q40 80 55 110 Q50 90 65 75" fill="{c["accent"]}" opacity="0.6"/>
      <path d="M135 65 Q160 80 145 110 Q150 90 135 75" fill="{c["accent"]}" opacity="0.6"/>'''
    face = f'''<circle cx="88" cy="95" r="4" fill="{c["eye"]}"/>
      <circle cx="112" cy="95" r="4" fill="{c["eye"]}"/>
      <circle cx="90" cy="93" r="1.5" fill="white"/>
      <circle cx="114" cy="93" r="1.5" fill="white"/>
      <ellipse cx="100" cy="110" rx="5" ry="3" fill="{c["outline"]}"/>'''
    extra = ""
    if p in ("teen",):
        extra = f'''<path d="M30 60 Q50 45 70 60" stroke="{c["rainbow"]}" fill="none" stroke-width="2" opacity="0.5"/>
          <path d="M30 65 Q50 50 70 65" stroke="#FFA500" fill="none" stroke-width="2" opacity="0.5"/>
          <path d="M30 70 Q50 55 70 70" stroke="#FFD700" fill="none" stroke-width="2" opacity="0.5"/>'''
    elif p == "legend":
        extra = f'''<text x="100" y="40" font-size="16" text-anchor="middle" fill="{c["stars"]}">⭐</text>'''
    return svg_base(horn + head + mane + face + extra)


def dragon_svg(p):
    c = PALETTES["dragon"][p]
    head = f'''<ellipse cx="100" cy="85" rx="40" ry="35" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>'''
    body = f'''<ellipse cx="100" cy="125" rx="50" ry="40" fill="{c["body"]}" stroke="{c["outline"]}" stroke-width="3"/>'''
    horns = f'''<path d="M68 58 L55 30 L78 52" fill="{c["outline"]}" stroke="{c["accent"]}" stroke-width="1"/>
      <path d="M132 58 L145 30 L122 52" fill="{c["outline"]}" stroke="{c["accent"]}" stroke-width="1"/>'''
    wings = f'''<path d="M50 95 Q20 70 35 110 Q30 90 50 100" fill="{c["accent"]}" stroke="{c["outline"]}" stroke-width="2" opacity="0.7"/>
      <path d="M150 95 Q180 70 165 110 Q170 90 150 100" fill="{c["accent"]}" stroke="{c["outline"]}" stroke-width="2" opacity="0.7"/>'''
    face = f'''<circle cx="86" cy="90" r="5" fill="{c["eye"]}"/>
      <circle cx="114" cy="90" r="5" fill="{c["eye"]}"/>
      <circle cx="88" cy="88" r="2" fill="white"/>
      <circle cx="116" cy="88" r="2" fill="white"/>
      <path d="M85 105 Q100 112 115 105" fill="none" stroke="{c["outline"]}" stroke-width="2"/>'''
    extra = ""
    if p == "deluxe":
        extra = f'''<text x="100" y="30" font-size="20" text-anchor="middle" fill="{c["crown"]}">👑</text>'''
    elif p == "legend":
        extra = f'''<ellipse cx="100" cy="125" rx="55" ry="45" fill="none" stroke="{c["glow"]}" stroke-width="3" opacity="0.4"/>
          <text x="100" y="50" font-size="22" text-anchor="middle" fill="{c["flame"]}">🔥</text>'''
    return svg_base(head + body + horns + wings + face + extra)


# ===== 分支进化SVG =====
BRANCH_SVGS = {
    "gold_ingot":  svg_base('<circle cx="100" cy="100" r="50" fill="#FFD700" stroke="#B8860B" stroke-width="3"/>'
                            '<text x="100" y="110" font-size="40" text-anchor="middle" fill="#B8860B">🪙</text>',
                            bg="#FFF8E7"),
    "love_arrow":  svg_base('<circle cx="100" cy="100" r="50" fill="#FF69B4" stroke="#C71585" stroke-width="3"/>'
                            '<text x="100" y="110" font-size="40" text-anchor="middle" fill="#C71585">🏹</text>',
                            bg="#FFF0F5"),
    "mech_core":   svg_base('<circle cx="100" cy="100" r="50" fill="#C0C0C0" stroke="#4A505A" stroke-width="3"/>'
                            '<text x="100" y="110" font-size="40" text-anchor="middle" fill="#4A505A">⚙️</text>',
                            bg="#F0F0F0"),
    "moon_stone":  svg_base('<circle cx="100" cy="100" r="50" fill="#E8E0F0" stroke="#8060A0" stroke-width="3"/>'
                            '<text x="100" y="110" font-size="40" text-anchor="middle" fill="#8060A0">🌙</text>',
                            bg="#F5F0FF"),
    "stardust":    svg_base('<circle cx="100" cy="100" r="50" fill="#1A1A4E" stroke="#4A4A8A" stroke-width="3"/>'
                            '<text x="100" y="110" font-size="40" text-anchor="middle" fill="#FFD700">✨</text>',
                            bg="#0A0A2A"),
    "fortune_bell": svg_base('<circle cx="100" cy="100" r="50" fill="#FF6347" stroke="#B84A30" stroke-width="3"/>'
                             '<text x="100" y="110" font-size="40" text-anchor="middle" fill="#B84A30">🎴</text>',
                             bg="#FFF5F0"),
}

# ===== 生成 =====
PET_FUNCS = {"pig": pig_svg, "fox": fox_svg, "cat": cat_svg, "unicorn": unicorn_svg, "dragon": dragon_svg}
FORMS = ["baby", "teen", "adult", "deluxe", "legend"]

os.makedirs(OUT, exist_ok=True)

for pt, func in PET_FUNCS.items():
    for f in FORMS:
        if pt in PALETTES and f in PALETTES[pt]:
            svg_content = func(f)
            path = os.path.join(OUT, f"{pt}_{f}.svg")
            with open(path, "w") as fp:
                fp.write(svg_content)
            print(f"✅ {pt}_{f}")
        else:
            print(f"⚠️  missing palette: {pt}_{f}")

for item_id, svg_content in BRANCH_SVGS.items():
    path = os.path.join(OUT, f"branch_{item_id}.svg")
    with open(path, "w") as fp:
        fp.write(svg_content)
    print(f"✅ branch_{item_id}")

print(f"\n🎉 共生成 {len(os.listdir(OUT))} 个 SVG 文件")
