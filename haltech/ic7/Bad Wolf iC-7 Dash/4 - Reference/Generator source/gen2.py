"""
Round 2: Bad Wolf splash options, three classic-style screens for the data
the physical gauges don't show, and a dense 20-tile diagnostic grid.
Reuses the drawing kit in gen.py. Run gen.py first, then this.
"""
import base64, json, sys
from pathlib import Path
from PIL import Image

import gen
from gen import (PILL_HOLES, W, H, DS, FACE, ang, pol, f, defs, ground, bezel, tick, text, lens, frange,
                 needle, svg, Renderer, diag_theme, PILLS, PILL_GEOM, pill_on)

ROOT = gen.ROOT
P = gen.OUT / "Haltech-iC7-CMDIY"
STOICH = 14.7


# ---------------------------------------------------------------- scalable small face
def face_gen(g, theme, k, major, minor, mid, labels, label_txt, unit_txt, extra=""):
    t = FACE[theme]
    cx, cy, rf = g["cx"], g["cy"], g["rf"]
    out = []
    majs = [round(x, 3) for x in major]
    for val in minor:
        d = ang(g, val)
        if round(val, 3) in majs:
            out.append(tick(cx, cy, d, rf - 5 * k, 11 * k, 3.4 * k, t["ink"], block=True))
        elif mid and any(abs(val - m) < 1e-6 for m in mid):
            out.append(tick(cx, cy, d, rf - 5 * k, 8 * k, 1.6 * k, t["ink"]))
        else:
            out.append(tick(cx, cy, d, rf - 5 * k, 5 * k, 1.1 * k, t["ink"]))
    for val, s in labels:
        x, y = pol(cx, cy, rf - 28 * k, ang(g, val))
        out.append(text(x, y, s, 17 * k, t["ink"], weight=500))
    if label_txt:
        out.append(text(cx, cy - 24 * k, label_txt, (13 if len(label_txt) > 3 else 15) * k, t["ink"], family="Outfit", weight=700, ls=1.4 * k))
    if unit_txt:
        out.append(text(cx, cy + 24 * k, unit_txt, 10 * k, t["ink2"], family="Outfit", weight=600, ls=0.8 * k))
    out.append(extra)
    return "".join(out)


def stoich_mark(g, theme, k=1.0, big=False):
    d = ang(g, STOICH)
    rf = g["rf"]
    if big:
        return tick(g["cx"], g["cy"], d, rf - 2, 26, 4, DS["orange"], block=True)
    return tick(g["cx"], g["cy"], d, rf - 2 * k, 14 * k, 2.6 * k, DS["orange"], block=True)


# gauge recipes: (vmin, vmax, major, minor, mid, labels, label, unit)
def recipe(kind):
    if kind == "afr":
        return (10, 20, frange(10, 20, 2), frange(10, 20, 0.5), frange(10, 20, 1),
                [(v, str(v)) for v in range(10, 21, 2)], "AFR", "AIR / FUEL")
    if kind == "oilt":
        return (50, 150, frange(50, 150, 20), frange(50, 150, 5), frange(50, 150, 10),
                [(v, str(v)) for v in range(50, 151, 20)], "OIL", "°C")
    if kind == "fuelp":
        return (0, 80, frange(0, 80, 20), frange(0, 80, 2), frange(0, 80, 10),
                [(v, str(v)) for v in range(0, 81, 20)], "FUEL", "PSI")
    if kind == "iat":
        return (0, 100, frange(0, 100, 20), frange(0, 100, 5), frange(0, 100, 10),
                [(v, str(v)) for v in range(0, 101, 20)], "AIR", "°C")
    if kind == "volts":
        return (8, 16, frange(8, 16, 2), frange(8, 16, 0.5), frange(8, 16, 1),
                [(v, str(v)) for v in range(8, 17, 2)], "VOLTS", "")
    if kind == "ign":
        return (-10, 50, frange(-10, 50, 10), frange(-10, 50, 2.5), frange(-10, 50, 5),
                [(v, str(v)) for v in range(-10, 51, 10)], "IGN", "°BTDC")
    raise KeyError(kind)


CHANNELS = {
    "afr": "Wideband O2 1 (internal WBO), as AFR",
    "oilt": "Oil Temperature (AVI10)",
    "fuelp": "Fuel Pressure (AVI11)",
    "iat": "Intake Air Temperature (AVI7)",
    "volts": "ECU Supply Voltage",
    "ign": "Ignition Angle",
    "afr_target": "Target AFR",
    "tps": "Throttle Position (DBW TPS 1)",
}
UNITS = {"afr": "AFR", "oilt": "°C", "fuelp": "psi", "iat": "°C", "volts": "V", "ign": "°BTDC"}


def small_gauge(kind, cx, cy, rb, rf, theme):
    vmin, vmax, major, minor, mid, labels, lab, unit = recipe(kind)
    g = dict(id=kind, cx=cx, cy=cy, rb=rb, rf=rf, vmin=vmin, vmax=vmax, a0=-135, a1=135)
    k = rf / 80
    extra = stoich_mark(g, theme, k) if kind == "afr" else ""
    if kind == "afr":
        unit = ""
    body = bezel(g, theme) + face_gen(g, theme, k, major, minor, mid, labels, lab, unit, extra=extra)
    return g, body


# ---------------------------------------------------------------- big AFR face
LAMPS2 = {}


def afr_big(cx, cy, theme, key):
    g = dict(id="afr_big", cx=cx, cy=cy, rb=196, rf=182, vmin=10, vmax=20, a0=-135, a1=135)
    t = FACE[theme]
    rf = g["rf"]
    out = [bezel(g, theme)]
    for i in range(0, 51):
        v = 10 + i * 0.2
        d = ang(g, v)
        if i % 5 == 0:
            out.append(tick(cx, cy, d, rf - 8, 15, 5, t["ink"], block=True))
        elif i % 5 in (2, 3) and False:
            pass
        else:
            out.append(tick(cx, cy, d, rf - 8, 7, 1.6, t["ink"]))
    for v in frange(10.5, 19.5, 1):
        out.append(tick(cx, cy, ang(g, v), rf - 8, 10, 2.2, t["ink"]))
    out.append(tick(cx, cy, ang(g, STOICH), rf - 2, 28, 5, DS["orange"], block=True))
    for v in range(10, 21, 2):
        d = ang(g, v)
        x, y = pol(cx, cy, rf - 46, d)
        rot = d if abs(d) <= 90 else d - (180 if d > 0 else -180)
        out.append(text(x, y, str(v), 40, t["ink"], weight=500, rot=rot))
    # inner lambda ring
    ri = 108
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{ri}" fill="none" stroke="{t["ink"]}" stroke-opacity="0.35" stroke-width="1.2"/>')
    lam = 0.70
    while lam <= 1.36 + 1e-9:
        afr = lam * STOICH
        if 10 <= afr <= 20:
            x, y = pol(cx, cy, ri - 6, ang(g, afr))
            big = abs(round(lam * 100) % 10) == 0
            out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{2.2 if big else 1.3}" fill="{t["ink2"]}"/>')
        lam = round(lam + 0.05, 2)
    for lam in (0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3):
        d = ang(g, lam * STOICH)
        x, y = pol(cx, cy, ri - 22, d)
        rot = d if abs(d) <= 90 else d - (180 if d > 0 else -180)
        out.append(text(x, y, f"{lam:.1f}", 14, t["ink2"], weight=500, rot=rot))
    # LCD: AFR / TGT
    lw, lh = 76, 36
    lx, ly = cx - lw / 2, cy - 64
    out.append(f'<rect x="{lx - 2}" y="{ly - 2}" width="{lw + 4}" height="{lh + 4}" rx="6" fill="{t["ink"]}" opacity="0.25"/>')
    out.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="5" fill="{t["lcd"]}"/>')
    out.append(text(lx + 5, ly + 10, "AFR", 5.5, t["lcd_ink"], family="Outfit", weight=600, anchor="start", ls=0.4))
    out.append(text(lx + 5, ly + 27, "TGT", 5.5, t["lcd_ink"], family="Outfit", weight=600, anchor="start", ls=0.4))
    # legends
    out.append(text(cx, cy + 40, "λ LAMBDA", 10, t["ink2"], family="Outfit", weight=600, ls=1.2))
    out.append(text(cx, cy + 66, "AIR / FUEL", 19, t["ink"], family="Outfit", weight=600, ls=1))
    out.append(text(cx - 62, cy + 92, "RICH", 9, t["ink2"], family="Outfit", weight=700, ls=1.6))
    out.append(text(cx + 62, cy + 92, "LEAN", 9, t["ink2"], family="Outfit", weight=700, ls=1.6))
    # throttle position window
    fw, fh = 104, 26
    fx, fy = cx - fw / 2, cy + 130
    out.append(text(cx, cy + 118, "THROTTLE", 10, t["ink"], family="Outfit", weight=600, ls=2.2))
    out.append(f'<rect x="{fx - 2}" y="{fy - 2}" width="{fw + 4}" height="{fh + 4}" rx="5" fill="{t["ink"]}" opacity="0.28"/>')
    out.append(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="4" fill="{t["window"]}"/>')
    for i, frac in enumerate((0, 0.25, 0.5, 0.75, 1)):
        x = fx + 8 + frac * (fw - 16)
        out.append(f'<line x1="{f(x)}" y1="{fy + fh - 2}" x2="{f(x)}" y2="{fy + fh - (7 if i % 2 == 0 else 5)}" stroke="{t["ink"]}" stroke-width="1.6"/>')
    out.append(text(fx + 9, fy + 7, "0", 10, t["ink"], anchor="start"))
    out.append(text(cx, fy + 7, "%", 10, t["ink"], family="Outfit", weight=600))
    out.append(text(fx + fw - 9, fy + 7, "100", 10, t["ink"], anchor="end"))
    # lamps
    for lid, sx, label in (("lamp_knock", -1, "KNOCK"), ("lamp_log", 1, "LOG")):
        x, y = cx + sx * 76, cy + 126
        out.append(lens(x, y, 9, theme))
        out.append(text(cx + sx * 76, cy + 146, label, 9, t["ink2"], family="Outfit", weight=600, ls=0.6))
        LAMPS2[(key, lid)] = dict(cx=x, cy=y, r=9)
    return g, "".join(out)


# ---------------------------------------------------------------- data plates (hybrid)
PLATES = [("oilt", "OIL TEMP", "°C", 50, 150, 0), ("fuelp", "FUEL PRESS", "PSI", 0, 80, 1),
          ("iat", "AIR TEMP", "°C", 0, 100, 0), ("volts", "BATTERY", "VOLTS", 8, 16, 1),
          ("ign", "IGNITION", "°BTDC", -10, 50, 1), ("inj", "INJ DUTY", "%", 0, 100, 0)]
PLATE_CH = dict(CHANNELS, inj="Injector Duty Cycle (primary)")


def plate(x, y, w, h, label, unit, vmin, vmax, theme):
    t = FACE[theme]
    out = [f'<rect x="{x - 3}" y="{y - 3}" width="{w + 6}" height="{h + 6}" rx="13" fill="#000" opacity="0.5" filter="url(#soft)"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="11" fill="url(#chromeA)"/>',
           f'<rect x="{x + 5}" y="{y + 5}" width="{w - 10}" height="{h - 10}" rx="7" fill="url(#faceG)"/>',
           f'<rect x="{x + 5.5}" y="{y + 5.5}" width="{w - 11}" height="{h - 11}" rx="7" fill="none" stroke="#000" stroke-opacity="0.18" stroke-width="1.5"/>']
    out.append(text(x + 16, y + 22, label, 12, t["ink"], family="Outfit", weight=700, anchor="start", ls=1.4))
    out.append(text(x + w - 16, y + 22, unit, 10, t["ink2"], family="Outfit", weight=600, anchor="end", ls=0.6))
    # scale track
    tx, ty, tw = x + 16, y + h - 36, w - 32
    out.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="5" rx="2.5" fill="{t["ink"]}" opacity="0.14"/>')
    for i in range(5):
        xx = tx + tw * i / 4
        out.append(f'<line x1="{f(xx)}" y1="{ty + 8}" x2="{f(xx)}" y2="{ty + (13 if i % 2 == 0 else 11)}" stroke="{t["ink"]}" stroke-width="1.2"/>')
    out.append(text(tx, ty + 18, str(vmin), 10, t["ink2"], anchor="start"))
    out.append(text(tx + tw, ty + 18, str(vmax), 10, t["ink2"], anchor="end"))
    comps = [dict(type="Text / Value", x=x + 14, y=y + 32, w=w - 28, h=54, font="Barlow Condensed SemiBold", size=54,
                  align="right", color=t["ink"]),
             dict(type="Bar Gauge (horizontal)", x=tx, y=ty, w=tw, h=5, min=vmin, max=vmax,
                  color=t["ink"] if theme == "day" else DS["orange_d"])]
    return "".join(out), comps


# ---------------------------------------------------------------- screens
def needle_spec(g, nfile, size, ch, unit):
    return dict(channel=ch, units=unit, display_min=round(g["vmin"], 2), display_max=round(g["vmax"], 2),
                start_angle_deg=g["a0"], end_angle_deg=g["a1"], sweep_deg=270, pivot_x=g["cx"], pivot_y=g["cy"],
                needle=nfile, needle_box=dict(x=g["cx"] - size // 2, y=g["cy"] - size // 2, w=size, h=size))


def screen_tuning(theme):
    parts = [ground(theme),
             f'<circle cx="430" cy="240" r="206" fill="#0b0b0c" opacity="0.85"/>']
    spec = {}
    g, body = afr_big(430, 240, theme, "tuning")
    parts.append(body)
    spec["afr"] = needle_spec(g, "needle_speedo_*_356px", 356, CHANNELS["afr"], "AFR")
    spec["afr_target"] = needle_spec(g, "needle_target_large_*_364px", 364, CHANNELS["afr_target"], "AFR")
    for kind, cx, cy in (("oilt", 134, 126), ("fuelp", 134, 354), ("volts", 726, 126), ("iat", 726, 354)):
        g, body = small_gauge(kind, cx, cy, 90, 80, theme)
        parts.append(body)
        spec[kind] = needle_spec(g, "needle_small_*_156px", 156, CHANNELS[kind], UNITS[kind])
    texts = {"afr_lcd": dict(x=396, y=177, w=68, h=17, channel=CHANNELS["afr"], font="Barlow Condensed SemiBold", size=15, color="#e9e04a", align="right"),
             "target_lcd": dict(x=396, y=194, w=68, h=17, channel=CHANNELS["afr_target"], font="Barlow Condensed SemiBold", size=15, color="#e9e04a", align="right"),
             "tps_bar": dict(type="Bar Gauge (horizontal)", x=386, y=383, w=88, h=5, channel=CHANNELS["tps"], min=0, max=100)}
    return svg(W, H, defs(theme) + "".join(parts)), dict(gauges=spec, text=texts)


SIX = [("afr", 143, 122), ("oilt", 430, 122), ("fuelp", 717, 122), ("iat", 143, 358), ("volts", 430, 358), ("ign", 717, 358)]


def screen_sixpack(theme):
    parts = [ground(theme)]
    spec = {}
    for kind, cx, cy in SIX:
        g, body = small_gauge(kind, cx, cy, 110, 100, theme)
        parts.append(body)
        spec[kind] = needle_spec(g, "needle_medium_*_192px", 192, CHANNELS[kind], UNITS[kind])
    return svg(W, H, defs(theme) + "".join(parts)), dict(gauges=spec)


def screen_hybrid(theme):
    parts = [ground(theme), f'<circle cx="236" cy="240" r="206" fill="#0b0b0c" opacity="0.85"/>']
    g, body = afr_big(236, 240, theme, "hybrid")
    parts.append(body)
    spec = {"afr": needle_spec(g, "needle_speedo_*_356px", 356, CHANNELS["afr"], "AFR"),
            "afr_target": needle_spec(g, "needle_target_large_*_364px", 364, CHANNELS["afr_target"], "AFR")}
    comps = []
    xs, ys, pw, ph = [470, 662], [26, 174, 322], 180, 132
    i = 0
    for r in range(3):
        for c in range(2):
            pid, lab, unit, vmin, vmax, dec = PLATES[i]
            body, cc = plate(xs[c], ys[r], pw, ph, lab, unit, vmin, vmax, theme)
            parts.append(body)
            for comp, suffix in zip(cc, ("value", "bar")):
                comp.update(id=f"{pid}_{suffix}", channel=PLATE_CH[pid])
                if suffix == "value":
                    comp["decimals"] = dec
                comps.append(comp)
            i += 1
    texts = {"afr_lcd": dict(x=202, y=177, w=68, h=17, channel=CHANNELS["afr"], font="Barlow Condensed SemiBold", size=15, color="#e9e04a", align="right"),
             "target_lcd": dict(x=202, y=194, w=68, h=17, channel=CHANNELS["afr_target"], font="Barlow Condensed SemiBold", size=15, color="#e9e04a", align="right"),
             "tps_bar": dict(type="Bar Gauge (horizontal)", x=192, y=383, w=88, h=5, channel=CHANNELS["tps"], min=0, max=100)}
    return svg(W, H, defs(theme) + "".join(parts)), dict(gauges=spec, plates=comps, text=texts)


# ---------------------------------------------------------------- dense diagnostic
DENSE = [
    ("boost", "BOOST", "PSI", "Manifold Pressure (gauge)", -10, 30, 1),
    ("boost_tgt", "BOOST TGT", "PSI", "Boost Target", -10, 30, 1),
    ("gear", "GEAR", "", "Gear Position (calculated from speed / RPM)", 0, 5, 0),
    ("afr", "AIR / FUEL", "AFR", "Wideband O2 1 (internal WBO)", 10, 20, 1),
    ("afr_tgt", "AFR TGT", "AFR", "Target AFR", 10, 20, 1),
    ("ign", "IGNITION", "°BTDC", "Ignition Angle", -10, 50, 1),
    ("knock", "KNOCK", "LVL", "Knock Level (KNOCK1)", 0, 100, 0),
    ("knock_ret", "KNOCK RET", "°", "Knock Retard", 0, 10, 1),
    ("inj", "INJ DUTY", "%", "Injector Duty Cycle (primary)", 0, 100, 0),
    ("inj_pw", "INJ PW", "MS", "Injection Time", 0, 20, 2),
    ("clt", "COOLANT", "°C", "Coolant Temperature (AVI3)", 30, 120, 0),
    ("oilp", "OIL PRESS", "PSI", "Oil Pressure (AVI4)", 0, 100, 0),
    ("oilt", "OIL TEMP", "°C", "Oil Temperature (AVI10)", 30, 150, 0),
    ("fuelp", "FUEL PRESS", "PSI", "Fuel Pressure (AVI11)", 0, 80, 1),
    ("iat", "INTAKE AIR", "°C", "Intake Air Temperature (AVI7)", -10, 80, 0),
    ("tps", "THROTTLE", "%", "Throttle Position (DBW TPS 1)", 0, 100, 0),
    ("pedal", "PEDAL", "%", "Pedal Position (APS A/B)", 0, 100, 0),
    ("brake", "BRAKE FRONT", "PSI", "Brake Pressure Front (SPI3)", 0, 1500, 0),
    ("batt", "BATTERY", "V", "ECU Supply Voltage", 10, 16, 1),
    ("cl_trim", "CL TRIM", "%", "Closed Loop Fuel Correction", -25, 25, 1),
]


def diag_dense(theme):
    T = diag_theme(theme)
    out = [f'<rect width="{W}" height="{H}" fill="{T["ground"]}"/>']
    nsp = []

    def tile(x, y, w, h, label, unit):
        out.append(f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="8" fill="{T["tile"]}" stroke="{T["border"]}"/>')
        out.append(text(x + 10, y + 14, label, 10, T["label"], family="Outfit", weight=600, anchor="start", ls=0.8))
        if unit:
            out.append(text(x + w - 10, y + 14, unit, 10, T["unit"], family="Outfit", weight=500, anchor="end", ls=0.3))

    # top row
    tile(8, 8, 160, 56, "RPM", "")
    nsp.append(dict(id="rpm_value", type="Text / Value", x=18, y=24, w=140, h=36, channel="Engine Speed (RPM)", font="Outfit SemiBold", size=32, align="right", color=T["ink"], decimals=0))
    tile(174, 8, 532, 56, "ENGINE SPEED", "x1000")
    tx, ty, tw, th = 186, 29, 508, 12
    out.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="3" fill="{T["track"]}"/>')
    rx0 = tx + tw * gen.REDLINE / gen.RPM_MAX
    out.append(f'<rect x="{f(rx0)}" y="{ty + th + 2}" width="{f(tx + tw - rx0)}" height="3" rx="1.5" fill="{T["warn"]}"/>')
    for kk in range(0, gen.RPM_MAX // 1000 + 1):
        xx = tx + tw * kk * 1000 / gen.RPM_MAX
        out.append(f'<line x1="{f(xx)}" y1="{ty + th + 2}" x2="{f(xx)}" y2="{ty + th + 6}" stroke="{T["tick"]}" stroke-width="1"/>')
        anchor = "start" if kk == 0 else ("end" if kk == gen.RPM_MAX // 1000 else "middle")
        out.append(text(xx, ty + th + 13, str(kk), 9, T["unit"], family="Outfit", weight=500, anchor=anchor))
    nsp.append(dict(id="rpm_bar", type="Bar Gauge (horizontal)", x=tx, y=ty, w=tw, h=th, channel="Engine Speed (RPM)", min=0, max=gen.RPM_MAX, warn_max=gen.REDLINE, color=T["fill"], warn_color=T["warn"]))
    tile(712, 8, 140, 56, "SPEED", "MPH")
    nsp.append(dict(id="speed_value", type="Text / Value", x=722, y=24, w=120, h=36, channel="Vehicle Speed (SPI1 drive train)", font="Outfit SemiBold", size=32, align="right", color=T["ink"], decimals=0))

    xs = [8, 178, 348, 518, 688]
    ys = [70, 162, 254, 346]
    tw_, th_ = 164, 86
    for i, (tid, lab, unit, ch, vmin, vmax, dec) in enumerate(DENSE):
        x, y = xs[i % 5], ys[i // 5]
        tile(x, y, tw_, th_, lab, unit)
        out.append(f'<rect x="{x + 10}" y="{y + th_ - 14}" width="{tw_ - 20}" height="4" rx="2" fill="{T["track"]}"/>')
        nsp.append(dict(id=f"{tid}_value", type="Text / Value", x=x + 10, y=y + 24, w=tw_ - 20, h=40, channel=ch,
                        font="Outfit SemiBold", size=32, align="right", color=T["ink"], decimals=dec, unit=unit,
                        display_min=vmin, display_max=vmax))
        nsp.append(dict(id=f"{tid}_bar", type="Bar Gauge (horizontal)", x=x + 10, y=y + th_ - 14, w=tw_ - 20, h=4,
                        channel=ch, min=vmin, max=vmax, color=T["fill"], warn_color=T["warn"]))
    # status row (same pills as the 12-tile screen)
    px, py, ph = 8, 446, 26
    for pid, plab, pch, sev in PILLS:
        pw = int(len(plab) * 7.4 + 26)
        # see-through pill: an indicator BEHIND the background lights it; the label is printed on top
        PILL_HOLES.append((px, py, pw, ph))
        out.append(f'<rect x="{px + .5}" y="{py + .5}" width="{pw - 1}" height="{ph - 1}" rx="{ph / 2}" fill="none" stroke="{T["border2"]}"/>')
        out.append(text(px + pw / 2, py + ph / 2, plab, 10.5, DS["on_fill"], family="Outfit", weight=700, ls=0.8))
        nsp.append(dict(id=f"pill_{pid}", type="Indicator / Image", x=px, y=py, w=pw, h=ph, channel=pch,
                        image_on=f"diagnostic/{theme}/pill_{pid}_on.png", severity=sev))
        px += pw + 6
    rx = W - 8
    out.append(text(rx - 46, py + ph / 2, "FUEL", 10.5, T["label"], family="Outfit", weight=600, anchor="end", ls=0.8))
    nsp.append(dict(id="fuel_value", type="Text / Value", x=rx - 42, y=py + 2, w=42, h=22, channel="Fuel Level 1 (PD16 SPI4)", font="Outfit SemiBold", size=18, align="right", color=T["ink"], unit="%"))
    out.append(text(rx - 136, py + ph / 2, "TRIM", 10.5, T["label"], family="Outfit", weight=600, anchor="end", ls=0.8))
    nsp.append(dict(id="trim_value", type="Text / Value", x=rx - 132, y=py + 2, w=30, h=22, channel="Rotary Trim Module 1 (Boost Trim)", font="Outfit SemiBold", size=18, align="right", color=T["ink"]))
    holes = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="#000"/>' for x, y, w, h in PILL_HOLES)
    out[0] = (f'<defs><mask id="pillcut" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
              f'<rect width="{W}" height="{H}" fill="#fff"/>{holes}</mask></defs>'
              f'<rect width="{W}" height="{H}" fill="{T["ground"]}" mask="url(#pillcut)"/>')
    PILL_HOLES.clear()
    return svg(W, H, "".join(out)), nsp


# ---------------------------------------------------------------- splash options
PLATE_FONT = "BarlowC"


def splash_plate():
    t = FACE["day"]
    pw, ph = 560, 132
    px, py = (W - pw) / 2, 128
    body = defs("day") + ground("day")
    body += f"""
<defs>
  <linearGradient id="silver" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.45" stop-color="#d8d8d8"/>
    <stop offset="0.55" stop-color="#a9a9a9"/><stop offset="1" stop-color="#e9e9e9"/>
  </linearGradient>
</defs>
<rect x="{px - 4}" y="{py - 4}" width="{pw + 8}" height="{ph + 8}" rx="14" fill="#000" opacity="0.6" filter="url(#soft)"/>
<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="10" fill="url(#chromeA)"/>
<rect x="{px + 6}" y="{py + 6}" width="{pw - 12}" height="{ph - 12}" rx="6" fill="#121213"/>
<rect x="{px + 12}" y="{py + 12}" width="{pw - 24}" height="{ph - 24}" rx="4" fill="none" stroke="#d8d8d8" stroke-opacity="0.55" stroke-width="2"/>
<circle cx="{px + 30}" cy="{py + ph / 2}" r="5" fill="url(#chromeA)"/>
<circle cx="{px + pw - 30}" cy="{py + ph / 2}" r="5" fill="url(#chromeA)"/>
"""
    # baseline = plate centre + half the cap height (Barlow Condensed caps are 0.70 em) so the capitals sit dead centre
    fs = 104
    body += (f'<text x="{W / 2 + 3}" y="{f(py + ph / 2 + fs * 0.70 / 2)}" font-family="{PLATE_FONT}" font-weight="600" font-size="{fs}" '
             f'fill="url(#silver)" text-anchor="middle" letter-spacing="6">BAD WOLF</text>')
    body += text(W / 2, 318, "TWINCAM  ·  TURBO", 18, DS["orange_d"], family="Outfit", weight=700, ls=6)
    body += f'<line x1="{W / 2 - 150}" y1="352" x2="{W / 2 + 150}" y2="352" stroke="{t["face_m"]}" stroke-opacity="0.35" stroke-width="1"/>'
    body += text(W / 2, 444, "CLASSIC MINI DIY", 9, "#8a8a90", family="Outfit", weight=600, ls=2.4)
    return svg(W, H, body)


def splash_dial():
    t = FACE["day"]
    g = dict(cx=430, cy=240, rb=206, rf=192, vmin=0, vmax=1, a0=-135, a1=135)
    body = defs("day") + ground("day") + f'<circle cx="430" cy="240" r="216" fill="#0b0b0c" opacity="0.85"/>' + bezel(g, "day")
    for i in range(0, 61):
        d = -135 + i * 4.5
        if i % 10 == 0:
            body += tick(430, 240, d, 184, 15, 5, t["ink"], block=True)
        elif i % 5 == 0:
            body += tick(430, 240, d, 184, 10, 2.2, t["ink"])
        else:
            body += tick(430, 240, d, 184, 7, 1.6, t["ink"])
    body += tick(430, 240, 135 - 9, 186, 20, 5, DS["orange"], block=True)
    body += text(430, 222, "BAD WOLF", 54, t["ink"], family="Outfit", weight=700, ls=2)
    body += f'<line x1="330" y1="262" x2="530" y2="262" stroke="{t["ink"]}" stroke-opacity="0.35" stroke-width="1"/>'
    body += text(430, 284, "TWINCAM · TURBO", 15, gen.DS["olive_text"], family="Outfit", weight=700, ls=5)
    body += text(430, 352, "CLASSIC MINI DIY", 8, t["ink2"], family="Outfit", weight=600, ls=1.6)
    return svg(W, H, body)


def splash_car_bg(src):
    """Illustration on the right, its band colours stretched across the left."""
    im = Image.open(src).convert("RGB").resize((480, 480), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H))
    canvas.paste(im, (W - 480, 0))
    edge = im.crop((0, 0, 1, 480)).resize((W - 480, 480))
    canvas.paste(edge, (0, 0))
    out = ROOT / "src" / "_car_bg.png"
    canvas.save(out)
    return out


def splash_car(bg_uri):
    body = f'<image href="{bg_uri}" x="0" y="0" width="{W}" height="{H}"/>'
    body += text(48, 150, "BAD", 112, "#efe9d8", family="Outfit", weight=700, anchor="start", ls=2)
    body += text(48, 262, "WOLF", 112, "#efe9d8", family="Outfit", weight=700, anchor="start", ls=2)
    body += f'<rect x="52" y="330" width="44" height="4" fill="{DS["orange"]}"/>'
    body += text(52, 358, "TWINCAM · TURBO", 16, "#1c1c20", family="Outfit", weight=700, anchor="start", ls=5)
    return svg(W, H, body)


# ---------------------------------------------------------------- main
def main():
    r = Renderer()
    spec_path = P / "nsp_layout_spec.json"
    spec = json.loads(spec_path.read_text())

    # splash
    r.render(splash_plate(), W, H, P / "splash/splash_bad_wolf_plate.png")
    r.render(splash_dial(), W, H, P / "splash/splash_bad_wolf_dial.png")
    illo = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if illo and illo.exists():
        bgp = splash_car_bg(illo)
        r.render(splash_car(bgp.as_uri()), W, H, P / "splash/splash_bad_wolf_car.png")
    old = P / "splash/splash_bad_wolf_800x480.png"
    if old.exists():
        old.rename(P / "splash/splash_cmdiy_logo.png")

    # classic-style data screens
    for name, fn in (("tuning", screen_tuning), ("sixpack", screen_sixpack), ("hybrid", screen_hybrid)):
        spec[f"classic_{name}"] = {}
        for theme in ("day", "night"):
            s, sp = fn(theme)
            r.render(s, W, H, P / f"classic_{name}/{theme}/classic_{name}_background_{theme}.png")
            if theme == "day":
                spec[f"classic_{name}"] = sp
            if "plates" in sp:
                spec[f"classic_{name}"].setdefault("plates_by_theme", {})[theme] = sp["plates"]
        spec[f"classic_{name}"].pop("plates", None)
    # lamps for the AFR face
    lamp_meta = {}
    for (key, lid), meta in LAMPS2.items():
        gen.LAMPS[lid] = meta
        lamp_meta.setdefault(key, {})[lid] = meta
    gen.LAMP_COLORS["lamp_knock"] = "#f5a00b"
    gen.LAMP_COLORS["lamp_log"] = "#3fcf6a"
    for lid in ("lamp_knock", "lamp_log"):
        s, size = gen.lamp_on(lid)
        r.render(s, size, size, P / f"classic/shared/lamps/{lid}_on_{size}px.png")
    for key in ("tuning", "hybrid"):
        spec[f"classic_{key}"]["lamps"] = {lid: dict(center_x=m["cx"], center_y=m["cy"], image=f"classic/shared/lamps/{lid}_on_44px.png",
                                                     place_x=round(m["cx"] - 22), place_y=round(m["cy"] - 22),
                                                     channel="Knock Level above threshold" if lid == "lamp_knock" else "Datalog Switch (Keypad B5) / logging active")
                                           for lid, m in lamp_meta[key].items()}

    # new needles
    for theme, col in (("day", "#151412"), ("night", DS["orange_d"])):
        for orient in ("up", "right"):
            s, size = needle(88, 20, 6, 2.6, 11, col, boss_color="#151412", orient=orient)
            r.render(s, size, size, P / f"classic/{theme}/needles/needle_medium_{theme}_{orient}_{size}px.png")
            s, size = needle(88, 20, 6, 2.6, 0, col, orient=orient)
            r.render(s, size, size, P / f"classic/{theme}/needles/nocap/needle_medium_{theme}_{orient}_nocap_{size}px.png")
            tcol = DS["orange"] if theme == "day" else "#e9e2cc"
            s, size = needle(174, 0, 4, 2, 0, tcol, orient=orient)
            r.render(s, size, size, P / f"classic/{theme}/needles/needle_target_large_{theme}_{orient}_{size}px.png")

    # dense diagnostic
    spec["diagnostic_dense"] = {}
    for theme in ("dark", "light"):
        s, nsp = diag_dense(theme)
        r.render(s, W, H, P / f"diagnostic_dense/{theme}/diagnostic_dense_background_{theme}.png")
        spec["diagnostic_dense"][theme] = nsp

    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    r.close()
    print("done")


if __name__ == "__main__":
    main()
