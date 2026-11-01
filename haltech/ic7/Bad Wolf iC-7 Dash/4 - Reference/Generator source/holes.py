"""
See-through slots in every background.

Bars, lamps and status pills all work the same way: a plain NSP component sits
BEHIND the background (lower Z) and the background has a transparent cut-out
where it should show. The cut-out gives it its shape (rounded bar ends, a round
lens, an arrow, a pill), so the component behind can be generic: a bar, or an
indicator that is just a block of colour.

- bars: cut here (rounded slots)
- lamps: cut here (round lenses, turn arrows); the chrome-ish ring stays printed
- pills: cut in the SVG itself (gen.py / gen2.py) so their printed labels stay on top

Run after gen.py, gen2.py and gen3.py. Writes holes.json (shape, position and the
off/track colour of every slot) for the composites and the bundle.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

import gen

P = gen.OUT / "Haltech-iC7-CMDIY"
SPEC = json.loads((P / "nsp_layout_spec.json").read_text())
SS = 4

TRACK = {"day": "#D6CDB4", "night": "#1D1C19", "plate_day": "#CCC5B3", "plate_night": "#403D37",
         "dark": "#333337", "light": "#EBEBEB"}
LENS_OFF = {"day": "#2A2620", "night": "#0D0C0B"}
ARROW_OFF = {"day": "#BDB49C", "night": "#45413A"}
PILL_OFF = {"dark": "#3A3A40", "light": "#E4E4E4"}
LAMP_ON = {"lamp_hb": "#4F8FF7", "lamp_ign": "#E8382C", "lamp_oil": "#E8382C", "lamp_cel": "#F5A00B",
           "lamp_fan": "#A9BF86", "lamp_turn_left": "#3FCF6A", "lamp_turn_right": "#3FCF6A",
           "lamp_knock": "#F5A00B", "lamp_log": "#3FCF6A"}
LAMP_R = {"lamp_hb": 9, "lamp_ign": 9, "lamp_knock": 9, "lamp_log": 9, "lamp_oil": 6.5, "lamp_fan": 6.5, "lamp_cel": 6.5}


def arrow_pts(cx, cy, s, direction):
    k = s / 18
    pts = [(-9, 0), (-1, -8), (-1, -4), (9, -4), (9, 4), (-1, 4), (-1, 8)]
    if direction == "right":
        pts = [(-px, py) for px, py in pts]
    return [(cx + px * k, cy + py * k) for px, py in pts]


def draw_shape(d, h, scale=1, fill=0, grow=0):
    if h["shape"] == "rrect":
        x, y, w, hh = h["x"] - grow, h["y"] - grow, h["w"] + 2 * grow, h["h"] + 2 * grow
        d.rounded_rectangle((x * scale, y * scale, (x + w) * scale - 1, (y + hh) * scale - 1),
                            radius=h["r"] * scale, fill=fill)
    elif h["shape"] == "circle":
        r = h["r"] + grow
        d.ellipse(((h["cx"] - r) * scale, (h["cy"] - r) * scale, (h["cx"] + r) * scale, (h["cy"] + r) * scale), fill=fill)
    else:
        d.polygon([(x * scale, y * scale) for x, y in h["pts"]], fill=fill)
        if grow:
            d.line([(x * scale, y * scale) for x, y in h["pts"] + h["pts"][:1]], fill=fill, width=int(2 * grow * scale))


def punch(path, hs):
    im = Image.open(path).convert("RGBA")
    mask = Image.new("L", (im.width * SS, im.height * SS), 255)
    d = ImageDraw.Draw(mask)
    for h in hs:
        if h.get("cut", True):
            draw_shape(d, h, SS, 0)
    mask = mask.resize(im.size, Image.LANCZOS)
    im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))
    im.save(path)


def bar(id_, x, y, w, h, off):
    return dict(id=id_, kind="bar", shape="rrect", x=x, y=y, w=w, h=h, r=min(h / 2, 4), off=off)


def bars_of(items, off):
    return [bar(c.get("id", ""), c["x"], c["y"], c["w"], c["h"], off) for c in items if c.get("type", "").startswith("Bar")]


def lamps_of(lamps, theme):
    out = []
    for lid, L in lamps.items():
        cx, cy = L["center_x"], L["center_y"]
        if lid.startswith("lamp_turn"):
            pts = arrow_pts(cx, cy, 20, "left" if lid.endswith("left") else "right")
            out.append(dict(id=lid, kind="lamp", shape="poly", pts=pts, cx=cx, cy=cy, x=round(cx - 13), y=round(cy - 13), w=26, h=26,
                            off=ARROW_OFF[theme], on=LAMP_ON[lid]))
        else:
            r = LAMP_R[lid]
            out.append(dict(id=lid, kind="lamp", shape="circle", cx=cx, cy=cy, r=r, x=round(cx - r - 3), y=round(cy - r - 3),
                            w=round(2 * r + 6), h=round(2 * r + 6), off=LENS_OFF[theme], on=LAMP_ON[lid]))
    return out


def pills_of(items, theme, T):
    sev_on = {"ok": T["fill"], "warn": T["caution"], "err": T["err"]}
    return [dict(id=c["id"], kind="pill", shape="rrect", x=c["x"], y=c["y"], w=c["w"], h=c["h"], r=c["h"] / 2,
                 off=PILL_OFF[theme], on=sev_on[c.get("severity", "ok")], cut=False)
            for c in items if c.get("type", "").startswith("Indicator")]


def main():
    holes, jobs = {}, []
    fb = SPEC["classic"]["fuel_bar"]
    for th in ("day", "night"):
        jobs.append((P / f"classic/{th}/classic_background_{th}.png",
                     [bar("fuel_bar", fb["x"], fb["y"], fb["w"], fb["h"], TRACK[th])] + lamps_of(SPEC["classic"]["lamps"], th)))
        wg = SPEC["classic_tuning"]["text"]["tps_bar"]
        jobs.append((P / f"classic_tuning/{th}/classic_tuning_background_{th}.png",
                     [bar("tps_bar", wg["x"], wg["y"], wg["w"], wg["h"], TRACK[th])] + lamps_of(SPEC["classic_tuning"]["lamps"], th)))
        wg = SPEC["classic_hybrid"]["text"]["tps_bar"]
        jobs.append((P / f"classic_hybrid/{th}/classic_hybrid_background_{th}.png",
                     [bar("tps_bar", wg["x"], wg["y"], wg["w"], wg["h"], TRACK[th])]
                     + bars_of(SPEC["classic_hybrid"]["plates_by_theme"][th], TRACK["plate_" + th])
                     + lamps_of(SPEC["classic_hybrid"]["lamps"], th)))
    for key in ("diagnostic", "diagnostic_dense"):
        for th in ("dark", "light"):
            T = gen.diag_theme(th)
            jobs.append((P / f"{key}/{th}/{key}_background_{th}.png",
                         bars_of(SPEC[key][th], TRACK[th]) + pills_of(SPEC[key][th], th, T)))
    E = P / "empty"
    slots = json.loads((E / "empty_slots.json").read_text())
    for layout, themes in (("five_gauge", ("day", "night")), ("six_pack", ("day", "night")), ("hybrid", ("day", "night")),
                           ("diagnostic", ("dark", "light")), ("diagnostic_dense", ("dark", "light"))):
        for th in themes:
            hs = []
            for s in slots[layout]:
                if s["kind"].startswith("Bar"):
                    off = TRACK["plate_" + th] if (layout == "hybrid" and s["slot"].startswith("Plate")) else TRACK[th]
                    b = s["box"]
                    hs.append(bar(s["slot"], b["x"], b["y"], b["w"], b["h"], off))
            if hs:
                jobs.append((E / f"{layout}/{layout}_empty_{th}.png", hs))
    for path, hs in jobs:
        punch(path, hs)
        holes[str(path.relative_to(P))] = hs
    (P / "holes.json").write_text(json.dumps(holes, indent=1))
    print("cut", len(jobs), "backgrounds")


def underlay(bg_path, lit=()):
    """Background composited over what sits behind it: bar tracks, lamp/pill colours (lit ids use their on colour)."""
    holes = json.loads((P / "holes.json").read_text())
    bg = Image.open(bg_path).convert("RGBA")
    rel = str(Path(bg_path).relative_to(P))
    base = Image.new("RGBA", bg.size, (0, 0, 0, 255))
    d = ImageDraw.Draw(base)
    for h in holes.get(rel, []):
        col = h["on"] if (h["id"] in lit and "on" in h) else h["off"]
        draw_shape(d, h, 1, col, grow=2)
    base.alpha_composite(bg)
    return base


if __name__ == "__main__":
    main()
