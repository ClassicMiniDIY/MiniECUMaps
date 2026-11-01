"""
True-empty backgrounds: the hardware only (chrome bezels, blank magnolia faces,
data plates, LCD/bar windows, diagnostic tiles). No labels, units, numerals,
ticks, scales, lamps or redlines, so any channel can go in any slot later.
NSP draws the ticks, numbers and labels itself. Run after gen.py / gen2.py.
"""
import json
from pathlib import Path

import gen, gen2
from gen import W, H, DS, FACE, defs, ground, bezel, svg, text, diag_theme, Renderer

P = gen.OUT / "Haltech-iC7-CMDIY"
E = P / "empty"


def window(x, y, w, h, fill, theme):
    t = FACE[theme]
    return (f'<rect x="{x - 2}" y="{y - 2}" width="{w + 4}" height="{h + 4}" rx="6" fill="{t["ink"]}" opacity="{0.25 if theme == "day" else 0.4}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{fill}"/>')


def big_slot(cx, cy, theme, slots, name):
    g = dict(cx=cx, cy=cy, rb=196, rf=182)
    t = FACE[theme]
    out = f'<circle cx="{cx}" cy="{cy}" r="206" fill="#0b0b0c" opacity="0.85"/>' + bezel(g, theme)
    lcd = (cx - 38, cy - 64, 76, 36)
    win = (cx - 52, cy + 130, 104, 26)
    out += window(*lcd, t["lcd"], theme) + window(*win, t["window"], theme)
    slots.append(dict(slot=name, kind="Large dial", cx=cx, cy=cy, face_d=2 * g["rf"],
                      box=dict(x=cx - g["rf"], y=cy - g["rf"], w=2 * g["rf"], h=2 * g["rf"])))
    slots.append(dict(slot=name + " · LCD window", kind="Text window", box=dict(x=lcd[0], y=lcd[1], w=lcd[2], h=lcd[3])))
    slots.append(dict(slot=name + " · lower window", kind="Bar / text window", box=dict(x=win[0], y=win[1], w=win[2], h=win[3])))
    slots.append(dict(slot=name + " · lower window bar", kind="Bar (behind background)", box=dict(x=cx - 44, y=cy + 143, w=88, h=5)))
    return out


def small_slot(cx, cy, rb, rf, theme, slots, name):
    g = dict(cx=cx, cy=cy, rb=rb, rf=rf)
    slots.append(dict(slot=name, kind="Dial", cx=cx, cy=cy, face_d=2 * rf,
                      box=dict(x=cx - rf, y=cy - rf, w=2 * rf, h=2 * rf)))
    return bezel(g, theme)


def five_gauge(theme):
    slots = []
    body = ground(theme) + big_slot(430, 240, theme, slots, "Centre")
    for name, cx, cy in (("Top left", 134, 126), ("Bottom left", 134, 354), ("Top right", 726, 126), ("Bottom right", 726, 354)):
        body += small_slot(cx, cy, 90, 80, theme, slots, name)
    return svg(W, H, defs(theme) + body), slots


def six_pack(theme):
    slots = []
    body = ground(theme)
    names = ["Top left", "Top centre", "Top right", "Bottom left", "Bottom centre", "Bottom right"]
    for name, (_, cx, cy) in zip(names, gen2.SIX):
        body += small_slot(cx, cy, 110, 100, theme, slots, name)
    return svg(W, H, defs(theme) + body), slots


def hybrid(theme):
    slots = []
    t = FACE[theme]
    body = ground(theme) + big_slot(236, 240, theme, slots, "Left dial")
    xs, ys, pw, ph = [470, 662], [26, 174, 322], 180, 132
    n = 1
    for r in range(3):
        for c in range(2):
            x, y = xs[c], ys[r]
            body += (f'<rect x="{x - 3}" y="{y - 3}" width="{pw + 6}" height="{ph + 6}" rx="13" fill="#000" opacity="0.5" filter="url(#soft)"/>'
                     f'<rect x="{x}" y="{y}" width="{pw}" height="{ph}" rx="11" fill="url(#chromeA)"/>'
                     f'<rect x="{x + 5}" y="{y + 5}" width="{pw - 10}" height="{ph - 10}" rx="7" fill="url(#faceG)"/>'
                     f'<rect x="{x + 5.5}" y="{y + 5.5}" width="{pw - 11}" height="{ph - 11}" rx="7" fill="none" stroke="#000" stroke-opacity="0.18" stroke-width="1.5"/>')
            slots.append(dict(slot=f"Plate {n}", kind="Data plate", box=dict(x=x + 5, y=y + 5, w=pw - 10, h=ph - 10)))
            slots.append(dict(slot=f"Plate {n} · bar", kind="Bar (behind background)", box=dict(x=x + 16, y=y + ph - 36, w=pw - 32, h=5)))
            n += 1
    return svg(W, H, defs(theme) + body), slots


def tiles(theme, rects, bars=()):
    T = diag_theme(theme)
    out = [f'<rect width="{W}" height="{H}" fill="{T["ground"]}"/>']
    slots = []
    for name, x, y, w, h, rx in rects:
        out.append(f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="{T["tile"]}" stroke="{T["border"]}"/>')
        slots.append(dict(slot=name, kind="Tile", box=dict(x=x, y=y, w=w, h=h)))
    for name, x, y, w, h in bars:
        slots.append(dict(slot=name, kind="Bar (behind background)", box=dict(x=x, y=y, w=w, h=h)))
    slots.append(dict(slot="Status strip", kind="Open area", box=dict(x=8, y=444, w=W - 16, h=30)))
    return svg(W, H, "".join(out)), slots


def diag12_rects():
    rects = []
    for c in gen.diag_layout():
        nm = {"rpm_tile": "Top 1 (wide-ish)", "rpmbar_tile": "Top 2 (long, for a bar)", "speed_tile": "Top 3"}.get(c["id"])
        if not nm:
            i = len(rects) - 3
            nm = f"Tile {i + 1} (row {i // 4 + 1}, col {i % 4 + 1})"
        rects.append((nm, c["x"], c["y"], c["w"], c["h"], 10))
    return rects


def dense_rects():
    rects = [("Top 1", 8, 8, 160, 56, 8), ("Top 2 (long, for a bar)", 174, 8, 532, 56, 8), ("Top 3", 712, 8, 140, 56, 8)]
    xs, ys = [8, 178, 348, 518, 688], [70, 162, 254, 346]
    for i in range(20):
        rects.append((f"Tile {i + 1} (row {i // 5 + 1}, col {i % 5 + 1})", xs[i % 5], ys[i // 5], 164, 86, 8))
    return rects


def diag12_bars():
    out = []
    for c in gen.diag_layout():
        if c["id"] == "rpmbar_tile":
            out.append(("Top 2 · bar", c["x"] + 14, c["y"] + 32, c["w"] - 28, 22))
        elif c["id"] not in ("rpm_tile", "speed_tile"):
            i = len([o for o in out if o[0].startswith("Tile")])
            out.append((f"Tile {i + 1} · bar", c["x"] + 12, c["y"] + c["h"] - 24, c["w"] - 24, 6))
    return out


def dense_bars():
    out = [("Top 2 · bar", 186, 29, 508, 12)]
    xs, ys = [8, 178, 348, 518, 688], [70, 162, 254, 346]
    for i in range(20):
        out.append((f"Tile {i + 1} · bar", xs[i % 5] + 10, ys[i // 5] + 72, 144, 4))
    return out


def pill_assets(r):
    out = {}
    for w in (60, 90, 120):
        s = svg(w, 26, f'<rect width="{w}" height="26" rx="13" fill="#ffffff"/>')
        p = E / f"pills/Pill_Blank_{w}_white.png"
        r.render(s, w, 26, p)
        out[f"mask{w}"] = p
        for theme in ("dark", "light"):
            T = diag_theme(theme)
            s = svg(w, 26, f'<rect x=".5" y=".5" width="{w - 1}" height="25" rx="12.5" fill="none" stroke="{T["border2"]}"/>')
            p = E / f"pills/Pill_Blank_{w}_Outline_{theme.title()}.png"
            r.render(s, w, 26, p)
    return out


def main():
    r = Renderer()
    spec = {}
    for name, fn, themes in (("five_gauge", five_gauge, ("day", "night")), ("six_pack", six_pack, ("day", "night")),
                             ("hybrid", hybrid, ("day", "night"))):
        for th in themes:
            s, slots = fn(th)
            r.render(s, W, H, E / f"{name}/{name}_empty_{th}.png")
        spec[name] = slots
    for name, rects, bars in (("diagnostic", diag12_rects(), diag12_bars()), ("diagnostic_dense", dense_rects(), dense_bars())):
        for th in ("dark", "light"):
            s, slots = tiles(th, rects, bars)
            r.render(s, W, H, E / f"{name}/{name}_empty_{th}.png")
        spec[name] = slots
    pill_assets(r)
    r.close()
    (E / "empty_slots.json").write_text(json.dumps(spec, indent=2))
    print("empty done")


if __name__ == "__main__":
    main()
