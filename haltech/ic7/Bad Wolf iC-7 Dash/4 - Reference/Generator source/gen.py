"""
Classic Mini DIY — Haltech iC-7 (800x480) dash asset generator.

Builds every PNG in the asset pack from SVG drawn here, renders with
Chromium (Playwright) at 1:1 pixels, and writes a component spec JSON
so every NSP component can be placed at an exact x/y/w/h.

Edit the CONFIG block and re-run to change ranges, redline, labels.
"""
import json, math, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
OUT = ROOT / "out"

# ---------------------------------------------------------------- CONFIG
W, H = 860, 480
REDLINE = 7000          # tacho + RPM bar redline start (rpm). Change to suit.
RPM_MAX = 8000
VEHICLE = "BAD WOLF TURBO MK2"
BRAND = "CLASSIC MINI DIY"

INHG_TO_PSI = 0.491154

# design-system colours (Classic Mini DIY tokens)
DS = {
    "olive": "#859369", "olive_d": "#9aac7f", "olive_text": "#5f6b45",
    "orange": "#ed7135", "orange_d": "#f08a54",
    "base100": "#ffffff", "base200": "#f2f2f2", "base300": "#e4e4e4", "ink": "#18181b",
    "base100_d": "#1f1f24", "base200_d": "#111116", "base300_d": "#09090d", "ink_d": "#e4e4e7",
    "fg2": "#4a4a4f", "fg3": "#636369", "fg2_d": "#b6b6bc", "fg3_d": "#9a9aa1",
    "warn": "#f59e0b", "warn_d": "#fbbf24", "err": "#b22222", "err_d": "#ef7676",
    "info": "#3b82f6", "info_d": "#60a5fa", "on_fill": "#1c1c20", "hero": "#242424",
}

# classic face palettes
FACE = {
    "day": dict(face_c="#efe9d8", face_m="#e8e1cc", face_e="#d2c9b0", ink="#1d1b18",
                ink2="#3a362f", lens="#2a2620", lens_ring="#8f8670", ghost="#bdb49c",
                ground="#1b1b1d", grain="#3b3b40", chrome=("#fbfbfb", "#cfcfcf", "#5d5d5f", "#c4c4c4", "#f2f2f2"),
                window="#d6cdb4", lcd="#0d0e0b", lcd_ink="#c9c03c"),
    "night": dict(face_c="#2a2824", face_m="#24221f", face_e="#171614", ink="#e9e2cc",
                  ink2="#b9b19b", lens="#0d0c0b", lens_ring="#4a463d", ghost="#45413a",
                  ground="#121214", grain="#26262a", chrome=("#9a9a9a", "#7a7a7a", "#2c2c2e", "#6c6c6c", "#8e8e8e"),
                  window="#1d1c19", lcd="#070806", lcd_ink="#8c862a"),
}

# ---------------------------------------------------------------- GAUGES
# angles: 0 deg = 12 o'clock, clockwise positive. 270 deg sweeps.
SPEEDO = dict(id="speedo", cx=430, cy=240, rb=196, rf=182, vmin=10, vmax=130, a0=-135, a1=135)
OIL    = dict(id="oil",    cx=134, cy=126, rb=90, rf=80, vmin=0, vmax=100, a0=-135, a1=135)
WATER  = dict(id="water",  cx=134, cy=354, rb=90, rf=80, vmin=30, vmax=110, a0=-135, a1=135)
TACHO  = dict(id="tacho",  cx=726, cy=126, rb=90, rf=80, vmin=0, vmax=RPM_MAX, a0=-135, a1=135)
BOOST  = dict(id="boost",  cx=726, cy=354, rb=90, rf=80, vmin=-20 * INHG_TO_PSI, vmax=30, a0=-135, a1=135)


def ang(g, v):
    return g["a0"] + (v - g["vmin"]) / (g["vmax"] - g["vmin"]) * (g["a1"] - g["a0"])


def pol(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def f(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- SVG BITS
def defs(theme="day"):
    c = FACE[theme]["chrome"]
    return f"""
<defs>
  <linearGradient id="chromeA" x1="0" y1="0" x2="0.35" y2="1">
    <stop offset="0" stop-color="{c[0]}"/><stop offset="0.28" stop-color="{c[1]}"/>
    <stop offset="0.52" stop-color="{c[2]}"/><stop offset="0.74" stop-color="{c[3]}"/>
    <stop offset="1" stop-color="{c[4]}"/>
  </linearGradient>
  <linearGradient id="chromeB" x1="0.35" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="{c[0]}"/><stop offset="0.35" stop-color="{c[1]}"/>
    <stop offset="0.6" stop-color="{c[2]}"/><stop offset="1" stop-color="{c[3]}"/>
  </linearGradient>
  <radialGradient id="faceG" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{FACE[theme]['face_c']}"/>
    <stop offset="0.82" stop-color="{FACE[theme]['face_m']}"/>
    <stop offset="1" stop-color="{FACE[theme]['face_e']}"/>
  </radialGradient>
  <radialGradient id="lensG" cx="0.4" cy="0.35" r="0.65">
    <stop offset="0" stop-color="#4a443a" stop-opacity="{0.9 if theme == 'day' else 0.5}"/>
    <stop offset="1" stop-color="{FACE[theme]['lens']}"/>
  </radialGradient>
  <filter id="crinkle" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.62" numOctaves="3" seed="7" result="n"/>
    <feDiffuseLighting in="n" lighting-color="{FACE[theme]['grain']}" surfaceScale="2.2" result="l">
      <feDistantLight azimuth="235" elevation="52"/>
    </feDiffuseLighting>
    <feComposite in="l" in2="SourceGraphic" operator="in"/>
  </filter>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="3"/>
  </filter>
</defs>"""


def ground(theme):
    t = FACE[theme]
    return (f'<rect width="{W}" height="{H}" fill="{t["ground"]}"/>'
            f'<rect width="{W}" height="{H}" fill="#000" filter="url(#crinkle)" opacity="0.9"/>')


def bezel(g, theme):
    cx, cy, rb, rf = g["cx"], g["cy"], g["rb"], g["rf"]
    mid, sw = (rb + rf) / 2, rb - rf
    return f"""
<g>
  <circle cx="{cx}" cy="{cy}" r="{rb + 3}" fill="#000" opacity="0.55" filter="url(#soft)"/>
  <circle cx="{cx}" cy="{cy}" r="{f(mid)}" fill="none" stroke="url(#chromeA)" stroke-width="{sw}"/>
  <circle cx="{cx}" cy="{cy}" r="{rf + 2}" fill="none" stroke="url(#chromeB)" stroke-width="3"/>
  <circle cx="{cx}" cy="{cy}" r="{rb - 0.5}" fill="none" stroke="#000" stroke-opacity="0.45" stroke-width="1"/>
  <circle cx="{cx}" cy="{cy}" r="{rf}" fill="url(#faceG)"/>
  <circle cx="{cx}" cy="{cy}" r="{rf - 1}" fill="none" stroke="#000" stroke-opacity="0.18" stroke-width="2"/>
</g>"""


def tick(cx, cy, deg, r_out, length, width, color, block=False):
    if block:
        return (f'<rect x="{f(cx - width / 2)}" y="{f(cy - r_out)}" width="{f(width)}" height="{f(length)}" '
                f'fill="{color}" transform="rotate({f(deg)} {cx} {cy})"/>')
    return (f'<line x1="{cx}" y1="{f(cy - r_out)}" x2="{cx}" y2="{f(cy - r_out + length)}" stroke="{color}" '
            f'stroke-width="{f(width)}" stroke-linecap="butt" transform="rotate({f(deg)} {cx} {cy})"/>')


def text(x, y, s, size, color, family="BarlowC", weight=600, anchor="middle", rot=None, ls=0, opacity=1):
    tr = f' transform="rotate({f(rot)} {f(x)} {f(y)})"' if rot is not None else ""
    lsa = f' letter-spacing="{ls}"' if ls else ""
    op = f' opacity="{opacity}"' if opacity != 1 else ""
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" font-weight="{weight}" font-size="{size}" '
            f'fill="{color}" text-anchor="{anchor}" dominant-baseline="central"{lsa}{op}{tr}>{s}</text>')


def lens(x, y, r, theme):
    t = FACE[theme]
    return (f'<circle cx="{f(x)}" cy="{f(y)}" r="{r + 1.5}" fill="{t["lens_ring"]}" opacity="0.6"/>'
            f'<circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="url(#lensG)"/>')


def arrow_path(x, y, s, direction):
    # arrow centred on x,y; s = overall width
    k = s / 18
    pts = [(-9, 0), (-1, -8), (-1, -4), (9, -4), (9, 4), (-1, 4), (-1, 8)]
    if direction == "right":
        pts = [(-px, py) for px, py in pts]
    return "M" + " L".join(f"{f(x + px * k)} {f(y + py * k)}" for px, py in pts) + " Z"


# ---------------------------------------------------------------- FACES
LAMPS = {}   # id -> dict(x,y,size,kind,color)


def face_speedo(theme):
    g, t = SPEEDO, FACE[theme]
    cx, cy, rf = g["cx"], g["cy"], g["rf"]
    out = []
    # mph ticks
    for v in range(10, 131, 2):
        d = ang(g, v)
        if v % 10 == 0:
            out.append(tick(cx, cy, d, rf - 8, 15, 5, t["ink"], block=True))
        elif v % 5 == 0:
            out.append(tick(cx, cy, d, rf - 8, 10, 2.2, t["ink"]))
        else:
            out.append(tick(cx, cy, d, rf - 8, 7, 1.6, t["ink"]))
    # mph numerals (odd tens, as on the real face), rotated with the dial
    for v in range(10, 131, 20):
        d = ang(g, v)
        x, y = pol(cx, cy, rf - 46, d)
        rot = d if abs(d) <= 90 else d - math.copysign(180, d)
        out.append(text(x, y, str(v), 40, t["ink"], weight=500, rot=rot))
    # inner km/h ring
    ri = 108
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{ri}" fill="none" stroke="{t["ink"]}" stroke-opacity="0.35" stroke-width="1.2"/>')
    for k in range(20, 211, 10):
        mph = k / 1.609344
        if mph < 10 or mph > 130:
            continue
        d = ang(g, mph)
        x, y = pol(cx, cy, ri - 6, d)
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{2.2 if k % 30 == 0 or k in (110, 140, 170, 200) else 1.3}" fill="{t["ink2"]}"/>')
    for k in (30, 60, 90, 110, 140, 170, 200):
        d = ang(g, k / 1.609344)
        x, y = pol(cx, cy, ri - 21, d)
        rot = d if abs(d) <= 90 else d - math.copysign(180, d)
        out.append(text(x, y, str(k), 15, t["ink2"], weight=500, rot=rot))
    # LCD odometer window
    lw, lh = 76, 36
    lx, ly = cx - lw / 2, cy - 64
    out.append(f'<rect x="{lx - 2}" y="{ly - 2}" width="{lw + 4}" height="{lh + 4}" rx="6" fill="{t["ink"]}" opacity="0.25"/>')
    out.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="5" fill="{t["lcd"]}"/>')
    out.append(text(lx + lw - 5, ly + 16, "MILES", 5.5, t["lcd_ink"], family="Outfit", weight=600, anchor="end", ls=0.4))
    out.append(text(lx + 5, ly + 27, "TRIP", 5.5, t["lcd_ink"], family="Outfit", weight=600, anchor="start", ls=0.4))
    # legends under hub
    out.append(text(cx, cy + 38, BRAND, 8, t["ink2"], family="Outfit", weight=600, ls=1.6))
    out.append(text(cx, cy + 56, "km/h", 12, t["ink2"], family="Outfit", weight=500))
    out.append(text(cx, cy + 76, "MPH", 21, t["ink"], family="Outfit", weight=600, ls=0.5))
    # fuel window
    fw, fh = 104, 26
    fx, fy = cx - fw / 2, cy + 130
    out.append(text(cx, cy + 118, "FUEL", 12, t["ink"], family="Outfit", weight=600, ls=3))
    out.append(f'<rect x="{fx - 2}" y="{fy - 2}" width="{fw + 4}" height="{fh + 4}" rx="5" fill="{t["ink"]}" opacity="0.28"/>')
    out.append(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="4" fill="{t["window"]}"/>')
    for i, frac in enumerate((0, 0.25, 0.5, 0.75, 1)):
        x = fx + 8 + frac * (fw - 16)
        out.append(f'<line x1="{f(x)}" y1="{fy + fh - 2}" x2="{f(x)}" y2="{fy + fh - (7 if i % 2 == 0 else 5)}" stroke="{t["ink"]}" stroke-width="1.6"/>')
    out.append(text(fx + 9, fy + 7, "E", 11, t["ink"], anchor="start"))
    out.append(text(cx, fy + 7, "½", 11, t["ink"], family="Outfit", weight=600))
    out.append(text(fx + fw - 9, fy + 7, "F", 11, t["ink"], anchor="end"))
    # lamps: H/B, IGN, turn arrows
    for lid, sx, label in (("lamp_hb", -1, "H/B"), ("lamp_ign", 1, "IGN")):
        x, y = cx + sx * 76, cy + 126
        out.append(lens(x, y, 9, theme))
        out.append(text(cx + sx * 86, cy + 150, label, 11, t["ink2"], family="Outfit", weight=600, rot=sx * -18))
        LAMPS[lid] = dict(cx=x, cy=y, r=9)
    for lid, sx, d in (("lamp_turn_left", -1, "left"), ("lamp_turn_right", 1, "right")):
        x, y = cx + sx * 116, cy + 50
        out.append(f'<path d="{arrow_path(x, y, 20, d)}" fill="{t["ghost"]}"/>')
        LAMPS[lid] = dict(cx=x, cy=y, r=11, arrow=d)
    return "".join(out)


def face_small(g, theme, major, minor, mid, labels, label_txt, unit_txt, lamp_id=None, extra=""):
    t = FACE[theme]
    cx, cy, rf = g["cx"], g["cy"], g["rf"]
    out = []
    v = g["vmin"]
    return_major = set(round(x, 3) for x in major)
    for val in minor:
        d = ang(g, val)
        rv = round(val, 3)
        if rv in return_major:
            out.append(tick(cx, cy, d, rf - 5, 11, 3.4, t["ink"], block=True))
        elif mid and any(abs(val - m) < 1e-6 for m in mid):
            out.append(tick(cx, cy, d, rf - 5, 8, 1.6, t["ink"]))
        else:
            out.append(tick(cx, cy, d, rf - 5, 5, 1.1, t["ink"]))
    for val, s in labels:
        d = ang(g, val)
        x, y = pol(cx, cy, rf - 28, d)
        out.append(text(x, y, s, 17, t["ink"], weight=500))
    out.append(text(cx, cy - 24, label_txt, 13 if len(label_txt) > 3 else 15, t["ink"], family="Outfit", weight=700, ls=1.4))
    if unit_txt:
        out.append(text(cx, cy + 24, unit_txt, 10, t["ink2"], family="Outfit", weight=600, ls=0.8))
    out.append(extra)
    if lamp_id:
        x, y = cx, cy + 55
        out.append(lens(x, y, 6.5, theme))
        LAMPS[lamp_id] = dict(cx=x, cy=y, r=6.5)
    return "".join(out)


def frange(a, b, step):
    n = int(round((b - a) / step))
    return [a + i * step for i in range(n + 1)]


def face_oil(theme):
    return face_small(OIL, theme, major=frange(0, 100, 20), minor=frange(0, 100, 5), mid=frange(0, 100, 10),
                      labels=[(v, str(v)) for v in range(0, 101, 20)], label_txt="OIL", unit_txt="PSI",
                      lamp_id="lamp_oil")


def face_water(theme):
    return face_small(WATER, theme, major=[30, 50, 70, 90, 100, 110], minor=frange(30, 110, 5), mid=frange(30, 110, 10),
                      labels=[(v, str(v)) for v in (30, 50, 70, 90, 100, 110)], label_txt="WATER", unit_txt="°C",
                      lamp_id="lamp_fan")


def face_tacho(theme):
    g, t = TACHO, FACE[theme]
    cx, cy, rf = g["cx"], g["cy"], g["rf"]
    # redline band
    a0, a1 = ang(g, REDLINE), ang(g, RPM_MAX)
    r = rf - 7
    p0, p1 = pol(cx, cy, r, a0), pol(cx, cy, r, a1)
    band = (f'<path d="M{f(p0[0])} {f(p0[1])} A{r} {r} 0 0 1 {f(p1[0])} {f(p1[1])}" fill="none" '
            f'stroke="{DS["orange"]}" stroke-width="6" opacity="{0.95 if theme == "day" else 0.8}"/>')
    extra = text(cx, cy + 36, "x100", 9, t["ink2"], family="Outfit", weight=600)
    body = face_small(g, theme, major=frange(0, RPM_MAX, 1000), minor=frange(0, RPM_MAX, 250), mid=frange(0, RPM_MAX, 500),
                      labels=[(v, str(v // 100)) for v in range(0, RPM_MAX + 1, 1000)], label_txt="", unit_txt="",
                      lamp_id="lamp_cel", extra=extra)
    rpm = text(cx, cy + 22, "RPM", 13, t["ink"], family="Outfit", weight=700, ls=2)
    return band + body + rpm


def face_boost(theme):
    g, t = BOOST, FACE[theme]
    vac = [-x * INHG_TO_PSI for x in range(20, 0, -2)]          # every 2 inHg
    vac_mid = [-x * INHG_TO_PSI for x in (20, 15, 10, 5)]
    vac_major = [-20 * INHG_TO_PSI, -10 * INHG_TO_PSI]
    pos = frange(0, 30, 1)
    labels = [(-20 * INHG_TO_PSI, "-20"), (-10 * INHG_TO_PSI, "-10")] + [(v, str(v)) for v in range(0, 31, 5)]
    extra = (text(g["cx"] - 5, g["cy"] + 24, "inHg", 9, t["ink2"], family="Outfit", weight=600, anchor="end") +
             f'<line x1="{g["cx"]}" y1="{g["cy"] + 19}" x2="{g["cx"]}" y2="{g["cy"] + 29}" stroke="{t["ink2"]}" stroke-width="1"/>' +
             text(g["cx"] + 5, g["cy"] + 24, "PSI", 9, t["ink2"], family="Outfit", weight=600, anchor="start", ls=0.6))
    return face_small(g, theme, major=vac_major + frange(0, 30, 5), minor=vac + pos, mid=vac_mid,
                      labels=labels, label_txt="BOOST", unit_txt="", extra=extra)


def classic_background(theme):
    t = FACE[theme]
    sp = SPEEDO
    collar = (f'<circle cx="{sp["cx"]}" cy="{sp["cy"]}" r="{sp["rb"] + 10}" fill="#0b0b0c" opacity="0.85"/>'
              f'<circle cx="{sp["cx"]}" cy="{sp["cy"]}" r="{sp["rb"] + 9.5}" fill="none" stroke="#fff" '
              f'stroke-opacity="{0.07 if theme == "day" else 0.04}" stroke-width="1"/>')
    parts = [ground(theme), collar]
    for g, face in ((SPEEDO, face_speedo), (OIL, face_oil), (WATER, face_water), (TACHO, face_tacho), (BOOST, face_boost)):
        parts.append(bezel(g, theme))
        parts.append(face(theme))
    return svg(W, H, defs(theme) + "".join(parts))


def face_only(g, facefn, theme):
    """Transparent PNG of one gauge (bezel + face), for free placement."""
    s = g["rb"] + 6
    gg = dict(g, cx=s, cy=s)
    # temporarily swap centre
    saved = dict(g)
    lamps_saved = {k: dict(v) for k, v in LAMPS.items()}
    g.update(cx=s, cy=s)
    body = bezel(g, theme) + facefn(theme)
    g.update(saved)
    LAMPS.clear(); LAMPS.update(lamps_saved)
    return svg(2 * s, 2 * s, defs(theme) + body), 2 * s


# ---------------------------------------------------------------- NEEDLES
def needle(L, tail, bw, tw, boss, color, boss_color=None, cap=None, size=None, orient="up", shadow=True):
    size = size or int(2 * (L + 8))
    c = size / 2
    pts = [(-bw / 2, tail), (-bw * 0.42, 0), (-tw / 2, -L + 7), (0, -L), (tw / 2, -L + 7), (bw * 0.42, 0), (bw / 2, tail)]
    d = "M" + " L".join(f"{f(c + x)} {f(c + y)}" for x, y in pts) + " Z"
    rot = 90 if orient == "right" else 0
    body = f'<path d="{d}" fill="{color}"/>'
    if tail > 0:
        body += f'<circle cx="{c}" cy="{f(c + tail)}" r="{f(bw / 2)}" fill="{color}"/>'
    if boss:
        bc = boss_color or color
        body += (f'<circle cx="{c}" cy="{c}" r="{boss}" fill="{bc}"/>'
                 f'<circle cx="{c}" cy="{c}" r="{boss}" fill="url(#bossG)"/>')
    if cap == "chrome":
        body += (f'<circle cx="{c}" cy="{c}" r="{boss * 0.62}" fill="url(#capG)"/>'
                 f'<circle cx="{c}" cy="{c}" r="{boss * 0.62}" fill="none" stroke="#000" stroke-opacity="0.35" stroke-width="0.8"/>')
    sh = ""
    if shadow:
        sh = f'<g filter="url(#nsh)" opacity="0.45"><g fill="#000">{body}</g></g>'
        sh = sh.replace(f'fill="{color}"', 'fill="#000"')
    d2 = f"""<defs>
<radialGradient id="bossG" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#fff" stop-opacity="0.10"/>
<stop offset="0.7" stop-color="#fff" stop-opacity="0.03"/><stop offset="1" stop-color="#000" stop-opacity="0.25"/></radialGradient>
<radialGradient id="capG" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffffff"/><stop offset="0.45" stop-color="#d9d9d9"/>
<stop offset="0.8" stop-color="#8a8a8a"/><stop offset="1" stop-color="#4c4c4c"/></radialGradient>
<filter id="nsh" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="1.6"/></filter></defs>"""
    return svg(size, size, d2 + f'<g transform="rotate({rot} {c} {c})">{sh}{body}</g>'), size


def cap_svg(r):
    s = int(2 * r + 6)
    c = s / 2
    return svg(s, s, f"""<defs><radialGradient id="capG" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffffff"/>
<stop offset="0.45" stop-color="#d9d9d9"/><stop offset="0.8" stop-color="#8a8a8a"/><stop offset="1" stop-color="#4c4c4c"/></radialGradient>
<filter id="b"><feGaussianBlur stdDeviation="1.2"/></filter></defs>
<circle cx="{c}" cy="{c}" r="{r}" fill="#000" opacity="0.5" filter="url(#b)"/>
<circle cx="{c}" cy="{c}" r="{r}" fill="url(#capG)"/>
<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="#000" stroke-opacity="0.35" stroke-width="0.8"/>"""), s


# ---------------------------------------------------------------- LAMPS (ON)
LAMP_COLORS = {
    "lamp_hb": "#4f8ff7", "lamp_ign": "#e8382c", "lamp_oil": "#e8382c", "lamp_cel": "#f5a00b",
    "lamp_fan": "#a9bf86", "lamp_turn_left": "#3fcf6a", "lamp_turn_right": "#3fcf6a",
}


def lamp_on(lid):
    meta = LAMPS[lid]
    col = LAMP_COLORS[lid]
    s = 44 if meta["r"] > 8 or "arrow" in meta else 32
    c = s / 2
    glow = f'<circle cx="{c}" cy="{c}" r="{c - 1}" fill="url(#gl)"/>'
    if "arrow" in meta:
        core = (f'<path d="{arrow_path(c, c, 20, meta["arrow"])}" fill="{col}"/>'
                f'<path d="{arrow_path(c, c, 20, meta["arrow"])}" fill="url(#hl)" opacity="0.6"/>')
    else:
        r = meta["r"]
        core = (f'<circle cx="{c}" cy="{c}" r="{r}" fill="{col}"/>'
                f'<circle cx="{c}" cy="{c}" r="{r}" fill="url(#hl)"/>')
    return svg(s, s, f"""<defs>
<radialGradient id="gl" cx="0.5" cy="0.5" r="0.5"><stop offset="0.25" stop-color="{col}" stop-opacity="0.55"/>
<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>
<radialGradient id="hl" cx="0.42" cy="0.38" r="0.6"><stop offset="0" stop-color="#fff" stop-opacity="0.85"/>
<stop offset="0.45" stop-color="#fff" stop-opacity="0.15"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>
{glow}{core}"""), s


# ---------------------------------------------------------------- DIAGNOSTIC GRID
DIAG_TILES = [
    # id, label, unit, channel (Haltech name, approx), min, max, decimals, secondary
    ("boost",   "BOOST",        "PSI",  "Manifold Pressure (gauge)",       -10, 30, 1, [("TGT", "Boost Target")]),
    ("afr",     "AIR / FUEL",   "AFR",  "Wideband O2 1 (internal WBO)",     10, 20, 1, [("TGT", "Target AFR / Lambda")]),
    ("ign",     "IGNITION",     "°BTDC","Ignition Angle",                  -10, 50, 1, []),
    ("inj",     "INJ DUTY",     "%",    "Injector Duty Cycle (primary)",     0, 100, 0, [("PW", "Injection Time (ms)")]),
    ("clt",     "COOLANT",      "°C",   "Coolant Temperature (AVI3)",       30, 120, 0, []),
    ("oilp",    "OIL PRESS",    "PSI",  "Oil Pressure (AVI4)",               0, 100, 0, []),
    ("oilt",    "OIL TEMP",     "°C",   "Oil Temperature (AVI10)",          30, 150, 0, []),
    ("fuelp",   "FUEL PRESS",   "PSI",  "Fuel Pressure (AVI11)",             0, 80, 1, []),
    ("iat",     "INTAKE AIR",   "°C",   "Intake Air Temperature (AVI7)",   -10, 80, 0, []),
    ("batt",    "BATTERY",      "V",    "ECU Supply Voltage",               10, 16, 1, []),
    ("tps",     "THROTTLE",     "%",    "Throttle Position (DBW TPS 1)",     0, 100, 0, [("PEDAL", "Pedal Position (APS A/B)")]),
    ("knock",   "KNOCK",        "LVL",  "Knock Level (KNOCK1)",              0, 100, 0, [("RET", "Knock Retard (°)")]),
]

PILLS = [("fan", "FAN", "Thermofan 1 Output (25A-HCO4)", "ok"),
         ("pump", "FUEL PUMP", "Primary Fuel Pump (PD16 25A-HCO3)", "ok"),
         ("cruise", "CRUISE", "Cruise Control Enable (Keypad B1)", "ok"),
         ("log", "LOGGING", "Datalog Switch (Keypad B5)", "ok"),
         ("cel", "CHECK ENGINE", "Check Engine Light (DPO5)", "warn"),
         ("kill", "KILL SW", "Kill Switch Input 1 (GenCond5)", "err")]


def diag_theme(theme):
    if theme == "dark":
        return dict(ground=DS["base200_d"], tile=DS["base100_d"], border="rgba(255,255,255,0.08)",
                    border2="rgba(255,255,255,0.14)", label=DS["fg2_d"], unit=DS["fg3_d"], ink=DS["ink_d"],
                    track="rgba(255,255,255,0.09)", fill=DS["olive_d"], warn=DS["orange_d"], err=DS["err_d"],
                    caution=DS["warn_d"], tick=DS["fg3_d"])
    return dict(ground=DS["base200"], tile=DS["base100"], border="rgba(0,0,0,0.10)", border2="rgba(0,0,0,0.16)",
                label=DS["fg2"], unit=DS["fg3"], ink=DS["ink"], track="rgba(0,0,0,0.08)", fill=DS["olive"],
                warn=DS["orange"], err=DS["err"], caution=DS["warn"], tick=DS["fg3"])


def diag_layout():
    comps = []
    # row A
    comps.append(dict(id="rpm_tile", kind="tile", x=8, y=8, w=190, h=80, label="RPM", unit=""))
    comps.append(dict(id="rpmbar_tile", kind="tile", x=204, y=8, w=472, h=80, label="ENGINE SPEED", unit="x1000"))
    comps.append(dict(id="speed_tile", kind="tile", x=682, y=8, w=170, h=80, label="SPEED", unit="MPH"))
    xs = [8, 220, 432, 644]
    ys = [94, 210, 326]
    i = 0
    for r in range(3):
        for c in range(4):
            t = DIAG_TILES[i]
            comps.append(dict(id=t[0] + "_tile", kind="tile", x=xs[c], y=ys[r], w=206, h=110, label=t[1], unit=t[2], ref=t))
            i += 1
    return comps


def diag_background(theme):
    T = diag_theme(theme)
    out = [f'<rect width="{W}" height="{H}" fill="{T["ground"]}"/>']
    nsp = []   # NSP component placements
    for cdef in diag_layout():
        x, y, w, h = cdef["x"], cdef["y"], cdef["w"], cdef["h"]
        out.append(f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="10" fill="{T["tile"]}" stroke="{T["border"]}"/>')
        out.append(text(x + 12, y + 17, cdef["label"], 11, T["label"], family="Outfit", weight=600, anchor="start", ls=0.9))
        if cdef["unit"]:
            out.append(text(x + w - 12, y + 17, cdef["unit"], 11, T["unit"], family="Outfit", weight=500, anchor="end", ls=0.4))
        if cdef["id"] == "rpm_tile":
            nsp.append(dict(id="rpm_value", type="Text / Value", x=x + 10, y=y + 28, w=w - 20, h=46, channel="Engine Speed (RPM)",
                            font="Outfit SemiBold", size=44, align="right", color=T["ink"], decimals=0))
        elif cdef["id"] == "speed_tile":
            nsp.append(dict(id="speed_value", type="Text / Value", x=x + 10, y=y + 28, w=w - 20, h=46, channel="Vehicle Speed (SPI1 drive train)",
                            font="Outfit SemiBold", size=44, align="right", color=T["ink"], decimals=0))
        elif cdef["id"] == "rpmbar_tile":
            tx, ty, tw, th = x + 14, y + 32, w - 28, 22
            out.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="4" fill="{T["track"]}"/>')
            rx0 = tx + tw * REDLINE / RPM_MAX
            out.append(f'<rect x="{f(rx0)}" y="{ty + th + 3}" width="{f(tx + tw - rx0)}" height="3" rx="1.5" fill="{T["warn"]}"/>')
            for k in range(0, RPM_MAX // 1000 + 1):
                xx = tx + tw * k * 1000 / RPM_MAX
                out.append(f'<line x1="{f(xx)}" y1="{ty + th + 3}" x2="{f(xx)}" y2="{ty + th + 8}" stroke="{T["tick"]}" stroke-width="1"/>')
                anchor = "start" if k == 0 else ("end" if k == RPM_MAX // 1000 else "middle")
                out.append(text(xx, ty + th + 16, str(k), 10, T["unit"], family="Outfit", weight=500, anchor=anchor))
            for k in range(1, RPM_MAX // 500):
                if k % 2:
                    xx = tx + tw * k * 500 / RPM_MAX
                    out.append(f'<line x1="{f(xx)}" y1="{ty + th + 3}" x2="{f(xx)}" y2="{ty + th + 6}" stroke="{T["tick"]}" stroke-width="1" opacity="0.7"/>')
            nsp.append(dict(id="rpm_bar", type="Bar Gauge (horizontal)", x=tx, y=ty, w=tw, h=th, channel="Engine Speed (RPM)",
                            min=0, max=RPM_MAX, warn_max=REDLINE, color=T["fill"], warn_color=T["warn"]))
        else:
            t = cdef["ref"]
            tid, lab, unit, ch, vmin, vmax, dec, sec = t
            # bar track + min/max legends
            bx, by, bw = x + 12, y + h - 24, w - 24
            out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="6" rx="3" fill="{T["track"]}"/>')
            out.append(text(bx, by + 15, str(vmin), 9, T["unit"], family="Outfit", weight=500, anchor="start"))
            out.append(text(bx + bw, by + 15, str(vmax), 9, T["unit"], family="Outfit", weight=500, anchor="end"))
            nsp.append(dict(id=f"{tid}_value", type="Text / Value", x=x + 84 if sec else x + 12, y=y + 30, w=w - 96 if sec else w - 24, h=44,
                            channel=ch, font="Outfit SemiBold", size=38, align="right", color=T["ink"], decimals=dec,
                            unit=unit, display_min=vmin, display_max=vmax))
            nsp.append(dict(id=f"{tid}_bar", type="Bar Gauge (horizontal)", x=bx, y=by, w=bw, h=6, channel=ch,
                            min=vmin, max=vmax, color=T["fill"], warn_color=T["warn"]))
            for j, (slab, sch) in enumerate(sec):
                sy = y + 46 + j * 20
                out.append(text(x + 12, sy, slab, 9, T["unit"], family="Outfit", weight=600, anchor="start", ls=0.8))
                vx = x + 12 + int(len(slab) * 7.2) + 7
                nsp.append(dict(id=f"{tid}_{slab.lower()}", type="Text / Value", x=vx, y=sy - 8, w=max(28, x + 82 - vx), h=16, channel=sch,
                                font="Outfit Medium", size=13, align="left", color=T["label"]))
    # status pills
    px, py, ph = 8, 446, 26
    for pid, plab, pch, sev in PILLS:
        pw = int(len(plab) * 7.4 + 26)
        # see-through pill: an indicator BEHIND the background lights it; the label is printed on top
        PILL_HOLES.append((px, py, pw, ph))
        out.append(f'<rect x="{px + .5}" y="{py + .5}" width="{pw - 1}" height="{ph - 1}" rx="{ph / 2}" fill="none" stroke="{T["border2"]}"/>')
        out.append(text(px + pw / 2, py + ph / 2, plab, 10.5, DS["on_fill"], family="Outfit", weight=700, ls=0.8))
        nsp.append(dict(id=f"pill_{pid}", type="Indicator / Image", x=px, y=py, w=pw, h=ph, channel=pch,
                        image_on=f"diagnostic/{theme}/pill_{pid}_on.png", severity=sev))
        PILL_GEOM[(theme, pid)] = (pw, ph, plab, sev)
        px += pw + 6
    # fuel + trim readouts on the right of the status row
    rx = W - 8
    out.append(text(rx - 46, py + ph / 2, "FUEL", 10.5, T["label"], family="Outfit", weight=600, anchor="end", ls=0.8))
    nsp.append(dict(id="fuel_value", type="Text / Value", x=rx - 42, y=py + 2, w=42, h=22, channel="Fuel Level 1 (PD16 SPI4)",
                    font="Outfit SemiBold", size=18, align="right", color=T["ink"], unit="%"))
    out.append(text(rx - 136, py + ph / 2, "TRIM", 10.5, T["label"], family="Outfit", weight=600, anchor="end", ls=0.8))
    nsp.append(dict(id="trim_value", type="Text / Value", x=rx - 132, y=py + 2, w=30, h=22, channel="Rotary Trim Module 1 (Boost Trim)",
                    font="Outfit SemiBold", size=18, align="right", color=T["ink"]))
    holes = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="#000"/>' for x, y, w, h in PILL_HOLES)
    out[0] = (f'<defs><mask id="pillcut" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
              f'<rect width="{W}" height="{H}" fill="#fff"/>{holes}</mask></defs>'
              f'<rect width="{W}" height="{H}" fill="{T["ground"]}" mask="url(#pillcut)"/>')
    PILL_HOLES.clear()
    return svg(W, H, "".join(out)), nsp


PILL_GEOM = {}
PILL_HOLES = []


def pill_on(theme, pid):
    T = diag_theme(theme)
    pw, ph, plab, sev = PILL_GEOM[(theme, pid)]
    fill = {"ok": T["fill"], "warn": T["caution"], "err": T["err"]}[sev]
    ink = DS["on_fill"] if (theme == "dark" or sev in ("ok", "warn")) else "#fafafa"
    if theme == "light" and sev == "ok":
        ink = DS["on_fill"]
    return svg(pw, ph, f'<rect width="{pw}" height="{ph}" rx="{ph / 2}" fill="{fill}"/>' +
               text(pw / 2, ph / 2, plab, 10.5, ink, family="Outfit", weight=700, ls=0.8)), pw, ph


# ---------------------------------------------------------------- SPLASH
def splash(logo_uri):
    bands = ""
    cols = [DS["olive"], DS["accent"] if "accent" in DS else "#6b7a52", "#5f6b45"]
    ys = [372, 404, 436]
    for i, (yy, col) in enumerate(zip(ys, ["#6b7a52", "#859369", "#5f6b45"])):
        bands += (f'<path d="M0 {yy} C 200 {yy - 26 + i * 6}, 520 {yy + 22 - i * 4}, 800 {yy - 12} L800 480 L0 480 Z" fill="{col}"/>')
    body = (f'<rect width="{W}" height="{H}" fill="{DS["hero"]}"/>{bands}'
            f'<image href="{logo_uri}" x="190" y="96" width="420" height="159"/>'
            + text(400, 296, VEHICLE, 15, DS["orange_d"], family="Outfit", weight=700, ls=4.5))
    return svg(W, H, body)


# ---------------------------------------------------------------- RENDER
def svg(w, h, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">{inner}</svg>')


FONT_CSS = "".join(
    f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url('file://{FONTS}/{fn}') format('truetype');}}"
    for fam, wt, fn in [("Outfit", 400, "Outfit-400.ttf"), ("Outfit", 500, "Outfit-500.ttf"), ("Outfit", 600, "Outfit-600.ttf"),
                        ("Outfit", 700, "Outfit-700.ttf"), ("BarlowC", 500, "BarlowCondensed-500.ttf"),
                        ("BarlowC", 600, "BarlowCondensed-600.ttf"), ("BarlowC", 700, "BarlowCondensed-700.ttf")])


class Renderer:
    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()
        self.page = self.browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        self.tmp = ROOT / "src" / "_r.html"

    def render(self, svg_str, w, h, path, scale=1):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        html = (f"<!doctype html><html><head><meta charset='utf-8'><style>{FONT_CSS}"
                f"html,body{{margin:0;background:transparent}}svg{{display:block}}</style></head>"
                f"<body>{svg_str}</body></html>")
        self.tmp.write_text(html)
        if scale != 1:
            pg = self.browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        else:
            pg = self.page
            pg.set_viewport_size({"width": w, "height": h})
        pg.goto(self.tmp.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(60)
        pg.screenshot(path=str(path), omit_background=True, clip={"x": 0, "y": 0, "width": w, "height": h})
        if scale != 1:
            pg.close()
        (path.with_suffix(".svg")).write_text(svg_str) if path.parent.name == "_svg" else None

    def close(self):
        self.browser.close()
        self.pw.stop()


# ---------------------------------------------------------------- MAIN
NEEDLES = {
    # name: (L, tail, base_w, tip_w, boss_r, cap)
    "speedo": (170, 34, 8.5, 3, 22, None),
    "small": (70, 16, 5, 2.2, 9, None),
    "tacho": (70, 16, 5, 2.2, 9, "chrome"),
    "telltale": (74, 0, 3.2, 1.8, 0, None),
}


def main():
    import base64
    r = Renderer()
    P = OUT / "Haltech-iC7-CMDIY"
    spec = {"screen": {"w": W, "h": H, "device": "Haltech iC-7 (800x480)"}, "classic": {}, "diagnostic": {}}

    # classic backgrounds + faces
    for theme in ("day", "night"):
        r.render(classic_background(theme), W, H, P / f"classic/{theme}/classic_background_{theme}.png")
        r.render(classic_background(theme), W, H, OUT / f"preview/classic_background_{theme}@2x.png", scale=2)
        for g, fn in ((SPEEDO, face_speedo), (OIL, face_oil), (WATER, face_water), (TACHO, face_tacho), (BOOST, face_boost)):
            s, size = face_only(g, fn, theme)
            r.render(s, size, size, P / f"classic/{theme}/faces/face_{g['id']}_{theme}_{size}px.png")
        # lamps are theme-independent but positions were collected during face drawing

    # needles
    for theme, col, boss_col in (("day", "#151412", "#151412"), ("night", DS["orange_d"], "#151412")):
        for name, (L, tail, bw, tw, boss, cap) in NEEDLES.items():
            if name == "telltale":
                ncol = DS["orange"] if theme == "day" else "#e9e2cc"
            else:
                ncol = col
            for orient in ("up", "right"):
                s, size = needle(L, tail, bw, tw, boss, ncol, boss_color=boss_col, cap=cap, orient=orient)
                r.render(s, size, size, P / f"classic/{theme}/needles/needle_{name}_{theme}_{orient}_{size}px.png")
                if name != "telltale":
                    s, size = needle(L, tail, bw, tw, 0, ncol, orient=orient)
                    r.render(s, size, size, P / f"classic/{theme}/needles/nocap/needle_{name}_{theme}_{orient}_nocap_{size}px.png")
    cs, csz = cap_svg(6)
    r.render(cs, csz, csz, P / f"classic/shared/cap_chrome_small_{csz}px.png")

    # lamps (on)
    for lid in LAMPS:
        s, size = lamp_on(lid)
        r.render(s, size, size, P / f"classic/shared/lamps/{lid}_on_{size}px.png")

    # diagnostic
    for theme in ("dark", "light"):
        s, nsp = diag_background(theme)
        r.render(s, W, H, P / f"diagnostic/{theme}/diagnostic_background_{theme}.png")
        r.render(s, W, H, OUT / f"preview/diagnostic_background_{theme}@2x.png", scale=2)
        for pid, *_ in PILLS:
            ps, pw, ph = pill_on(theme, pid)
            r.render(ps, pw, ph, P / f"diagnostic/{theme}/pill_{pid}_on.png")
        spec["diagnostic"][theme] = nsp

    # splash
    logo = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if logo and logo.exists():
        uri = "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode()
        r.render(splash(uri), W, H, P / "splash/splash_bad_wolf_800x480.png")

    # classic spec
    def needle_spec(g, nname, unit, ch, note=""):
        L = NEEDLES[nname][0]
        size = int(2 * (L + 8))
        return dict(channel=ch, units=unit, display_min=round(g["vmin"], 2), display_max=round(g["vmax"], 2),
                    start_angle_deg=g["a0"], end_angle_deg=g["a1"], sweep_deg=g["a1"] - g["a0"],
                    pivot_x=g["cx"], pivot_y=g["cy"], needle_image_px=size,
                    needle_box=dict(x=g["cx"] - size // 2, y=g["cy"] - size // 2, w=size, h=size), note=note)
    spec["classic"]["gauges"] = {
        "speedo": needle_spec(SPEEDO, "speedo", "mph", "Vehicle Speed (SPI1 drive train)",
                              "Face starts at 10 mph. If NSP clamps at display min, the needle rests on 10; set min 0 and start angle -157.5 to let it drop below like the real Smiths."),
        "tacho": needle_spec(TACHO, "tacho", "rpm", "Engine Speed (RPM)", f"Redline band printed from {REDLINE} rpm."),
        "oil": needle_spec(OIL, "small", "psi", "Oil Pressure (AVI4)"),
        "water": needle_spec(WATER, "small", "°C", "Coolant Temperature (AVI3)"),
        "boost": needle_spec(BOOST, "small", "psi (gauge)", "Manifold Pressure (OBPS 1) shown as gauge pressure",
                             "Linear scale: -20 inHg (-9.82 psi) to +30 psi. In kPa gauge: -67.7 to 206.8. In kPa absolute (101.3 baro): 33.6 to 308.1."),
    }
    spec["classic"]["lamps"] = {k: dict(center_x=round(v["cx"], 1), center_y=round(v["cy"], 1),
                                        image=f"classic/shared/lamps/{k}_on_{lamp_on(k)[1]}px.png",
                                        place_x=round(v["cx"] - lamp_on(k)[1] / 2), place_y=round(v["cy"] - lamp_on(k)[1] / 2))
                                for k, v in LAMPS.items()}
    sp = SPEEDO
    spec["classic"]["text"] = {
        "odometer": dict(x=sp["cx"] - 34, y=sp["cy"] - 63, w=48, h=17, channel="Odometer", font="Barlow Condensed SemiBold", size=15, color="#e9e04a", align="right"),
        "trip": dict(x=sp["cx"] - 14, y=sp["cy"] - 46, w=48, h=17, channel="Trip Meter", font="Barlow Condensed SemiBold", size=15, color="#e9e04a", align="right"),
    }
    spec["classic"]["fuel_bar"] = dict(type="Bar Gauge (horizontal)", x=sp["cx"] - 44, y=sp["cy"] + 143, w=88, h=5,
                                       channel="Fuel Level 1 (PD16 SPI4)", min=0, max=100, color="#1d1b18", night_color=DS["orange_d"])
    (P / "nsp_layout_spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    r.close()
    print("done")


if __name__ == "__main__":
    main()
