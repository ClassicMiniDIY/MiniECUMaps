"""
Needles v2: tight, tall, narrow strips (no empty padding), pointing straight up.

NSP sizes and positions a needle image from its own bounds, so the square,
padded images from v1 never pivoted correctly. Here every needle image is only
as wide as the needle and only as tall as tip-to-tail. Two variants:

- tail  (recommended): Smiths-style counterweight; pivot exactly 80% down from
  the top, so Needle Image Offset is -80% for every needle.
- plain: no tail; pivot exactly on the bottom edge.

The black boss / chrome cap is NOT part of the needle any more: it's a separate
round "hub" image placed on top at the pivot (round, so it never needs to turn).

Also rebuilds the square preview needles (pivot centred) from these strips so
the composites show exactly what the strips produce.
"""
import json, math
from pathlib import Path
from PIL import Image

import gen
from gen import svg, Renderer, DS

P = gen.OUT / "Haltech-iC7-CMDIY"
V2 = P / "needles_v2"
TAIL_FRAC = 0.25          # tail = L/4  ->  pivot at L/(L+L/4) = 80% from the top

NEEDLES = {
    # key: (L, base_w, tip_w, hub_r, hub_style, square size of the v1 preview file, v1 file stem)
    "large":    (170, 8.5, 3.0, 22, "black",  356, "needle_speedo"),
    "tacho":    (70, 5.0, 2.2, 9, "chrome", 156, "needle_tacho"),
    "small":    (70, 5.0, 2.2, 9, "black",  156, "needle_small"),
    "medium":   (88, 6.0, 2.6, 11, "black", 192, "needle_medium"),
    "peakrpm":  (74, 3.2, 1.8, 0, None,     164, "needle_telltale"),
    "afrtarget": (174, 4.0, 2.0, 0, None,   364, "needle_target_large"),
}


def colour(key, theme):
    if key in ("peakrpm", "afrtarget"):
        return DS["orange"] if theme == "day" else "#e9e2cc"
    return "#151412" if theme == "day" else DS["orange_d"]


def strip_svg(L, bw, tw, col, tail):
    w = int(math.ceil(bw)) + 4
    w += w % 2
    c = w / 2
    t = L * TAIL_FRAC if tail else 0
    h = int(round(L + t))
    pts = [(c, 0), (c + tw / 2, 7), (c + bw * 0.42, L)]
    if tail:
        pts += [(c + bw / 2, h), (c - bw / 2, h)]
    else:
        pts += [(c + bw / 2, L), (c - bw / 2, L)]
    pts += [(c - bw * 0.42, L), (c - tw / 2, 7)]
    d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z"
    return svg(w, h, f'<path d="{d}" fill="{col}"/>'), w, h


def hub_svg(r, style):
    s = int(2 * r + 4)
    c = s / 2
    body = f"""<defs><radialGradient id="b" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#fff" stop-opacity="0.10"/>
<stop offset="0.7" stop-color="#fff" stop-opacity="0.03"/><stop offset="1" stop-color="#000" stop-opacity="0.25"/></radialGradient>
<radialGradient id="cap" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffffff"/><stop offset="0.45" stop-color="#d9d9d9"/>
<stop offset="0.8" stop-color="#8a8a8a"/><stop offset="1" stop-color="#4c4c4c"/></radialGradient></defs>
<circle cx="{c}" cy="{c}" r="{r}" fill="#151412"/><circle cx="{c}" cy="{c}" r="{r}" fill="url(#b)"/>"""
    if style == "chrome":
        body += (f'<circle cx="{c}" cy="{c}" r="{r * 0.62:.2f}" fill="url(#cap)"/>'
                 f'<circle cx="{c}" cy="{c}" r="{r * 0.62:.2f}" fill="none" stroke="#000" stroke-opacity="0.35" stroke-width="0.8"/>')
    return svg(s, s, body), s


def main():
    r = Renderer()
    meta = {}
    for key, (L, bw, tw, hr, hs, sq, stem) in NEEDLES.items():
        for theme in ("day", "night"):
            col = colour(key, theme)
            for variant in ("tail", "plain"):
                s, w, h = strip_svg(L, bw, tw, col, variant == "tail")
                p = V2 / theme / f"needle_{key}_{theme}_{variant}.png"
                r.render(s, w, h, p)
                meta[f"{key}_{theme}_{variant}"] = dict(file=str(p.relative_to(P)), w=w, h=h, pivot_y=L,
                                                        offset_pct=-round(100 * L / h) if variant == "tail" else 0)
        if hr:
            s, size = hub_svg(hr, hs)
            p = V2 / f"hub_{key}.png"
            r.render(s, size, size, p)
            meta[f"hub_{key}"] = dict(file=str(p.relative_to(P)), size=size)
    r.close()
    (V2 / "needles_v2.json").write_text(json.dumps(meta, indent=1))

    # square, pivot-centred previews built from the strips (+ hub) for the composites
    for key, (L, bw, tw, hr, hs, sq, stem) in NEEDLES.items():
        for theme in ("day", "night"):
            m = meta[f"{key}_{theme}_tail"]
            strip = Image.open(P / m["file"]).convert("RGBA")
            canvas = Image.new("RGBA", (sq, sq), (0, 0, 0, 0))
            canvas.alpha_composite(strip, (sq // 2 - m["w"] // 2, sq // 2 - L))
            if hr:
                hub = Image.open(P / meta[f"hub_{key}"]["file"]).convert("RGBA")
                canvas.alpha_composite(hub, (sq // 2 - hub.width // 2, sq // 2 - hub.height // 2))
            canvas.save(P / f"classic/{theme}/needles/{stem}_{theme}_up_{sq}px.png")
    print("needles v2 done")


if __name__ == "__main__":
    main()
