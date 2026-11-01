"""
Assemble the upload-ready bundle for the Haltech iC-7 (NSP) and render the
install-guide PDF. Run after gen.py and gen2.py (860x480 build).
"""
import csv, json, re, shutil, sys, html
from pathlib import Path

import gen, gen2, holes as HO

ROOT = gen.ROOT
SRC = gen.OUT / "Haltech-iC7-CMDIY"
B = gen.OUT / "bundle" / "Bad Wolf iC-7 Dash"
SPEC = json.loads((SRC / "nsp_layout_spec.json").read_text())
W, H = gen.W, gen.H

# ------------------------------------------------------------------ white lamp masks
def white_lamps():
    gen.classic_background("day")          # fills gen.LAMPS (classic lamp geometry)
    gen2.screen_tuning("day")              # fills gen2.LAMPS2 (knock / log)
    for (key, lid), meta in gen2.LAMPS2.items():
        gen.LAMPS[lid] = meta
    saved = dict(gen.LAMP_COLORS)
    r = gen.Renderer()
    out = {}
    for lid in list(gen.LAMPS):
        gen.LAMP_COLORS[lid] = "#ffffff"
        s, size = gen.lamp_on(lid)
        p = ROOT / "out" / "_white" / f"{lid}_white.png"
        r.render(s, size, size, p)
        out[lid] = p
    r.close()
    gen.LAMP_COLORS.update(saved)
    return out


LAMP_COLOR = {"lamp_hb": "#4F8FF7", "lamp_ign": "#E8382C", "lamp_oil": "#E8382C", "lamp_cel": "#F5A00B",
              "lamp_fan": "#A9BF86", "lamp_turn_left": "#3FCF6A", "lamp_turn_right": "#3FCF6A",
              "lamp_knock": "#F5A00B", "lamp_log": "#3FCF6A"}
LAMP_NAME = {"lamp_hb": "Lamp_HighBeam", "lamp_ign": "Lamp_Ignition", "lamp_oil": "Lamp_OilPressure", "lamp_cel": "Lamp_CheckEngine",
             "lamp_fan": "Lamp_Fan", "lamp_turn_left": "Lamp_TurnLeft", "lamp_turn_right": "Lamp_TurnRight",
             "lamp_knock": "Lamp_Knock", "lamp_log": "Lamp_Logging"}
LAMP_CH = {"lamp_hb": "Head Light Input (PD16 AVI2) or your high-beam channel",
           "lamp_ign": "Battery Voltage Light (PD16 HBO1)", "lamp_oil": "Oil Pressure Light (DPO3)",
           "lamp_cel": "Check Engine Light (DPO5)", "lamp_fan": "Thermofan 1 (25A-HCO4)",
           "lamp_turn_left": "Left Indicator Output (PD16 8A-HCO6)", "lamp_turn_right": "Right Indicator Output (PD16 8A-HCO2)",
           "lamp_knock": "Knock Level (KNOCK1) over your threshold", "lamp_log": "Datalog Switch (Keypad B5)"}

NEEDLE_FILE = {  # spec needle pattern -> (src glob stem, friendly name)
    "speedo": ("needles_v2/{t}/needle_large_{t}_tail.png", "Needle_Large_{T}.png"),
    "tacho": ("needles_v2/{t}/needle_tacho_{t}_tail.png", "Needle_Tacho_{T}.png"),
    "small": ("needles_v2/{t}/needle_small_{t}_tail.png", "Needle_Small_{T}.png"),
    "medium": ("needles_v2/{t}/needle_medium_{t}_tail.png", "Needle_Medium_{T}.png"),
    "telltale": ("needles_v2/{t}/needle_peakrpm_{t}_tail.png", "Needle_PeakRPM_{T}.png"),
    "target": ("needles_v2/{t}/needle_afrtarget_{t}_tail.png", "Needle_AFRTarget_{T}.png"),
}
HUB = {"speedo": "large", "tacho": "tacho", "small": "small", "medium": "medium"}
HUB_BY_NEEDLE = {"Needle_Large": "large", "Needle_Tacho": "tacho", "Needle_Small": "small", "Needle_Medium": "medium"}
V2META = json.loads((SRC / "needles_v2" / "needles_v2.json").read_text()) if (SRC / "needles_v2" / "needles_v2.json").exists() else {}


def needle_kind(pattern):
    for k in ("speedo", "tacho", "small", "medium", "telltale"):
        if f"needle_{k}" in pattern:
            return k
    if "target_large" in pattern:
        return "target"
    raise KeyError(pattern)


# ------------------------------------------------------------------ rows
def dial_row(name, g, needle_names, z, ch=None, note=""):
    b = g["needle_box"]
    return dict(component=name, type="Dial gauge (Retro circular)", file=needle_names, x=b["x"], y=b["y"], w=b["w"], h=b["h"],
                z=z, channel=ch or g["channel"], _pivot=(g["pivot_x"], g["pivot_y"]),
                settings=f"Min {g['display_min']} / Max {g['display_max']} {g['units']} · Start −135° · End 135° · "
                         f"Needle Image Offset −80% · palette off except Needle · "
                         f"Centre ({g['pivot_x']}, {g['pivot_y']}){(' · ' + note) if note else ''}")


def lamp_row(lid, L, z):
    h = HO.lamps_of({lid: L}, "day")[0]
    shape = "arrow" if lid.startswith("lamp_turn") else "round lens"
    return dict(component=LAMP_NAME[lid].replace("Lamp_", "") + " lamp", type="Indicator", file="Indicator_Fill_white.png",
                x=h["x"], y=h["y"], w=h["w"], h=h["h"], z=z, channel=L.get("channel") or LAMP_CH[lid],
                settings=f"Behind background ({shape}) · On {LAMP_COLOR[lid]} · "
                         f"Off {HO.ARROW_OFF['day'] if shape == 'arrow' else HO.LENS_OFF['day']} day / "
                         f"{HO.ARROW_OFF['night'] if shape == 'arrow' else HO.LENS_OFF['night']} night")


def text_row(name, t, z, color=None):
    return dict(component=name, type="Numeric gauge", file="", x=t["x"], y=t["y"], w=t["w"], h=t["h"], z=z,
                channel=t["channel"],
                settings=f"Value only · {t.get('font', 'Outfit SemiBold')} {t.get('size', '')}px · "
                         f"{t.get('align', 'right')}-aligned · {color or t.get('color', '')}"
                         + (f" · {t['decimals']} dp" if "decimals" in t else ""))


TRACKS = {"window": "#D6CDB4 day · #1D1C19 night", "plate": "#CCC5B3 day · #403D37 night", "tile": "#333337 dark · #EBEBEB light"}


def bar_row(name, t, z, color, track="tile"):
    return dict(component=name, type="Bar gauge (horizontal)", file="", x=t["x"], y=t["y"], w=t["w"], h=t["h"], z=z,
                channel=t["channel"],
                settings=f"Behind background · Min {t.get('min', 0)} / Max {t.get('max', 100)} · fill {color} · track {TRACKS[track]} · frame off")


def bg_row(fname):
    return dict(component="Background", type="Image", file=fname, x=0, y=0, w=W, h=H, z=1, channel="—",
                settings="Fill the whole screen. Above the bars, below everything else. Its see-through slots show the bars underneath.")


SCREENS = []
SLUG = {"A": "classic", "B": "tuning", "C": "sixpack", "D": "hybrid", "E": "diagnostic", "F": "diagnostic_dense"}


def nm(S, name):
    """Prefix a file name with the screen's slug, lower-case: classic_background_day.png."""
    return f"{SLUG[S['key']]}_{name.lower()}"


def finish(S):
    """Add hub images, rename file references in the rows and set the layer order (bars/lamps/pills behind the background)."""
    hubs = []
    for r in S["rows"]:
        if r["type"].startswith("Dial") and r["z"] == 4:
            kind = next((v for k, v in HUB_BY_NEEDLE.items() if r["file"].startswith(k)), None)
            if kind:
                size = V2META[f"hub_{kind}"]["size"]
                px, py = r["_pivot"]
                hubs.append(dict(component=f"{r['component']} hub", type="Image", file=f"Hub_{kind.title()}.png",
                                 x=px - size // 2, y=py - size // 2, w=size, h=size, z=99, channel="—",
                                 settings="Round centre cap on top of the needle at the pivot. Never rotates."))
    S["rows"].extend(hubs)
    tok = re.compile(r"([A-Za-z0-9]+(?:_[A-Za-z0-9]+)*(?:/[A-Za-z]+)?\.png)")
    for r in S["rows"]:
        for k in ("file", "settings"):
            r[k] = tok.sub(lambda m: nm(S, m.group(1)), r[k])
        t = r["type"]
        if t == "Image" and r["component"].endswith("hub"):
            r["z"] = 5
        else:
            r["z"] = 0 if (t.startswith("Bar") or t == "Indicator") else 1 if t == "Image" else 2 if t.startswith("Numeric") else (3 if r["z"] == 3 else 4)


def classic_screens():
    s = SPEC["classic"]
    rows = [bg_row("Background_Day.png  (or Background_Night.png)")]
    for lid, L in s["lamps"].items():
        L = dict(L, channel=LAMP_CH[lid])
        rows.append(lamp_row(lid, L, 1))
    rows.append(text_row("Odometer", s["text"]["odometer"], 2, "#E9E04A day · #C9C03C night"))
    rows.append(text_row("Trip", s["text"]["trip"], 2, "#E9E04A day · #C9C03C night"))
    fb = dict(s["fuel_bar"])
    rows.append(bar_row("Fuel level bar", fb, 2, "#1D1B18 day · #F08A54 night", "window"))
    g = s["gauges"]
    rows.append(dial_row("Tacho peak marker (optional)", dict(g["tacho"], needle_box=dict(x=g["tacho"]["pivot_x"] - 82, y=g["tacho"]["pivot_y"] - 82, w=164, h=164)),
                         "Needle_PeakRPM_Day/Night.png", 3, "Peak / max RPM channel, if your firmware has one"))
    names = {"speedo": ("Speedometer", "large"), "tacho": ("Tachometer", "tacho"), "oil": ("Oil pressure", "small"),
             "water": ("Water temp", "small"), "boost": ("Boost", "small")}
    for k, (nm, n) in names.items():
        fn = {"large": "Needle_Large", "tacho": "Needle_Tacho", "small": "Needle_Small"}[n]
        note = "Face starts at 10 mph: to let the needle rest below 10, use Min 0 and Start −157.5°" if k == "speedo" else \
               ("Linear −20 inHg (−9.82 psi) to +30 psi; in kPa(g): −67.7 / 206.8" if k == "boost" else "")
        rows.append(dial_row(nm, g[k], f"{fn}_Day/Night.png", 4, note=note))
    SCREENS.append(dict(key="A", folder="A - Classic", title="Classic", src_dir="classic", themes=("day", "night"),
                        needles=["speedo", "tacho", "small", "telltale"], lamps=list(s["lamps"]), pills=False,
                        previews=["preview_classic_day.png", "preview_classic_night.png"], rows=rows,
                        blurb="The HMW pod redrawn for the iC-7: speedo with odometer and fuel window, oil, water, tacho and boost."))


def tuning_like(key, folder, title, skey, src_dir, blurb, needles):
    s = SPEC[skey]
    rows = [bg_row("Background_Day.png  (or Background_Night.png)")]
    for lid, L in s.get("lamps", {}).items():
        rows.append(lamp_row(lid, L, 1))
    t = s.get("text", {})
    if "afr_lcd" in t:
        rows.append(text_row("AFR (LCD)", t["afr_lcd"], 2, "#E9E04A day · #C9C03C night"))
        rows.append(text_row("AFR target (LCD)", t["target_lcd"], 2, "#E9E04A day · #C9C03C night"))
        rows.append(bar_row("Throttle bar", t["tps_bar"], 2, "#1D1B18 day · #F08A54 night", "window"))
    pd = s.get("plates_by_theme", {})
    if pd:
        for c, cn in zip(pd["day"], pd["night"]):
            nm = c["id"].replace("_value", " value").replace("_bar", " bar").replace("oilt", "Oil temp").replace("fuelp", "Fuel press") \
                .replace("iat", "Air temp").replace("volts", "Battery").replace("ign", "Ignition").replace("inj", "Inj duty")
            if c["type"].startswith("Text"):
                rows.append(text_row(nm, c, 2, f"{c['color']} day · {cn['color']} night"))
            else:
                rows.append(bar_row(nm, c, 2, f"{c['color']} day · {cn['color']} night", "plate"))
    labels = {"afr": "Air / fuel", "afr_target": "AFR target needle", "oilt": "Oil temp", "fuelp": "Fuel pressure",
              "iat": "Intake air", "volts": "Volts", "ign": "Ignition timing"}
    for k, g in s["gauges"].items():
        kind = needle_kind(g["needle"])
        fn = NEEDLE_FILE[kind][1].replace("_{T}.png", "_Day/Night.png")
        z = 3 if k == "afr_target" else 4
        note = "Sits under the main AFR needle" if k == "afr_target" else ""
        rows.append(dial_row(labels[k], g, fn, z, note=note))
    SCREENS.append(dict(key=key, folder=folder, title=title, src_dir=src_dir, themes=("day", "night"), needles=needles,
                        lamps=list(s.get("lamps", {})), pills=False,
                        previews=[f"preview_{src_dir}_day.png", f"preview_{src_dir}_night.png"], rows=rows, blurb=blurb))


def diag_screen(key, folder, title, skey, src_dir, blurb):
    rows = [bg_row("Background_Dark.png  (or Background_Light.png)")]
    dark, light = SPEC[skey]["dark"], SPEC[skey]["light"]
    for c, cl in zip(dark, light):
        if c["type"].startswith("Indicator"):
            Td, Tl = gen.diag_theme("dark"), gen.diag_theme("light")
            sk = {"ok": "fill", "warn": "caution", "err": "err"}[c.get("severity", "ok")]
            rows.append(dict(component=c["id"].replace("pill_", "").upper() + " pill", type="Indicator", file="Indicator_Fill_white.png",
                             x=c["x"], y=c["y"], w=c["w"], h=c["h"], z=0, channel=c["channel"],
                             settings=f"Behind background (pill; label printed) · On {Td[sk]} dark / {Tl[sk]} light · "
                                      f"Off {HO.PILL_OFF['dark']} dark / {HO.PILL_OFF['light']} light"))
        elif c["type"].startswith("Bar"):
            rows.append(bar_row(c["id"].replace("_", " "), c, 2, f"{c['color']} dark · {cl['color']} light"))
        else:
            rows.append(text_row(c["id"].replace("_", " "), c, 2, f"{c['color']} dark · {cl['color']} light"))
    SCREENS.append(dict(key=key, folder=folder, title=title, src_dir=src_dir, themes=("dark", "light"), needles=[], lamps=[],
                        pills=True, previews=[f"preview_{src_dir}_dark.png", f"preview_{src_dir}_light.png"], rows=rows, blurb=blurb))


# ------------------------------------------------------------------ copy files
FILL = ROOT / "out" / "_white" / "indicator_fill_white.png"


def assemble(white):
    FILL.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image as _I
    _I.new("RGBA", (64, 64), (255, 255, 255, 255)).save(FILL)
    if B.exists():
        shutil.rmtree(B)
    B.mkdir(parents=True)
    fonts = B / "1 - Fonts"
    fonts.mkdir()
    names = {"Outfit-400": "Outfit-Regular", "Outfit-500": "Outfit-Medium", "Outfit-600": "Outfit-SemiBold", "Outfit-700": "Outfit-Bold",
             "BarlowCondensed-500": "BarlowCondensed-Medium", "BarlowCondensed-600": "BarlowCondensed-SemiBold",
             "BarlowCondensed-700": "BarlowCondensed-Bold"}
    for k, v in names.items():
        shutil.copy(gen.FONTS / f"{k}.ttf", fonts / f"{v}.ttf")
    (fonts / "LICENSE.txt").write_text(
        "Outfit and Barlow Condensed are released under the SIL Open Font License 1.1, free for personal and commercial use.\n"
        "Full licence text: https://openfontlicense.org\n"
        "Outfit: https://fonts.google.com/specimen/Outfit\nBarlow Condensed: https://fonts.google.com/specimen/Barlow+Condensed\n")
    sp = B / "2 - Splash Screen"
    sp.mkdir()
    shutil.copy(SRC / "splash/splash_bad_wolf_plate.png", sp / "splash_bad_wolf_plate.png")
    shutil.copy(SRC / "splash/splash_bad_wolf_dial.png", sp / "splash_bad_wolf_dial.png")
    shutil.copy(SRC / "splash/splash_bad_wolf_car.png", sp / "splash_bad_wolf_car.png")
    scr = B / "3 - Screens"
    for S in SCREENS:
        d = scr / S["folder"]
        d.mkdir(parents=True)
        for th in S["themes"]:
            T = th.title()
            if S["src_dir"] == "classic":
                bg = SRC / f"classic/{th}/classic_background_{th}.png"
            elif S["src_dir"].startswith("classic_"):
                bg = SRC / f"{S['src_dir']}/{th}/{S['src_dir']}_background_{th}.png"
            else:
                bg = SRC / f"{S['src_dir']}/{th}/{S['src_dir']}_background_{th}.png"
            shutil.copy(bg, d / nm(S, f"Background_{T}.png"))
            for kind in S["needles"]:
                stem, friendly = NEEDLE_FILE[kind]
                shutil.copy(SRC / stem.format(t=th), d / nm(S, friendly.format(T=T)))
        for kind in S["needles"]:
            if kind in HUB:
                shutil.copy(SRC / f"needles_v2/hub_{HUB[kind]}.png", d / nm(S, f"Hub_{HUB[kind].title()}.png"))
        if S["pills"] or S["lamps"]:
            shutil.copy(FILL, d / nm(S, "Indicator_Fill_white.png"))
        pv = d / "Previews (not for import)"
        pv.mkdir()
        for p in S["previews"]:
            shutil.copy(SRC / "previews" / p, pv / nm(S, "preview_" + p.rsplit("_", 1)[1]))
        with open(d / nm(S, "components.csv"), "w", newline="") as fh:
            wcsv = csv.writer(fh)
            wcsv.writerow(["Step", "Component", "NSP type", "File", "X", "Y", "X size", "Y size", "Z", "Channel", "Settings"])
            for i, r in enumerate(S["rows"], 1):
                wcsv.writerow([i, r["component"], r["type"], r["file"], r["x"], r["y"], r["w"], r["h"], r["z"], r["channel"], r["settings"]])
    ref = B / "4 - Reference"
    ref.mkdir()
    shutil.copy(SRC / "nsp_layout_spec.json", ref / "nsp_layout_spec.json")
    shutil.copytree(SRC / "needles_v2", ref / "Alternate needles (no-tail versions, offset 0%)",
                    ignore=shutil.ignore_patterns("*_tail.png", "*.json", "hub_*"))
    shutil.copytree(ROOT / "src", ref / "Generator source", ignore=shutil.ignore_patterns("_*", "__pycache__", "*.bak"))


# ------------------------------------------------------------------ PDF
def esc(x):
    return html.escape(str(x))


def table(rows):
    out = ['<table class="t" style="table-layout:fixed"><colgroup><col style="width:3%"><col style="width:11%"><col style="width:8%">'
           '<col style="width:17%"><col style="width:4%"><col style="width:4%"><col style="width:4.5%"><col style="width:4.5%"><col style="width:2.5%">'
           '<col style="width:13%"><col style="width:28.5%"></colgroup><thead><tr><th>#</th><th>Component</th><th>NSP type</th><th>File</th><th>X</th><th>Y</th>'
           '<th>X size</th><th>Y size</th><th>Z</th><th>Channel</th><th>Settings</th></tr></thead><tbody>']
    for i, r in enumerate(rows, 1):
        out.append(f'<tr><td class="n">{i}</td><td><b>{esc(r["component"])}</b></td><td>{esc(r["type"])}</td><td class="f">{esc(r["file"])}</td>'
                   f'<td class="n">{r["x"]}</td><td class="n">{r["y"]}</td><td class="n">{r["w"]}</td><td class="n">{r["h"]}</td>'
                   f'<td class="n">{r["z"]}</td><td>{esc(r["channel"])}</td><td class="s">{esc(r["settings"])}</td></tr>')
    out.append("</tbody></table>")
    return "".join(out)


def guide_html():
    FONT = "".join(f"@font-face{{font-family:'Outfit';font-weight:{w};src:url('file://{gen.FONTS}/Outfit-{w}.ttf')}}" for w in (400, 500, 600, 700))
    prev = lambda p: (SRC / "previews" / p).as_uri()
    splash = (SRC / "splash/splash_bad_wolf_plate.png").as_uri()
    css = f"""{FONT}
@page {{ size: Letter; margin: 0.55in 0.55in 0.6in; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Outfit, sans-serif; color: #18181b; font-size: 10.5pt; line-height: 1.55; margin: 0; }}
h1 {{ font-size: 30pt; line-height: 1.1; margin: 0 0 8pt; font-weight: 700; }}
h2 {{ font-size: 17pt; margin: 0 0 8pt; font-weight: 700; break-after: avoid; }}
h3 {{ font-size: 12.5pt; margin: 14pt 0 4pt; font-weight: 700; break-after: avoid; }}
p {{ margin: 0 0 7pt; }}
.eyebrow {{ font-size: 9pt; font-weight: 600; letter-spacing: .08em; color: #a4471f; text-transform: uppercase; margin-bottom: 4pt; }}
.page {{ break-before: page; }}
.lede {{ font-size: 12pt; color: #4a4a4f; max-width: 6.2in; }}
.cover img {{ width: 100%; border-radius: 8pt; margin: 14pt 0; }}
.box {{ background: #f2f2f2; border-radius: 8pt; padding: 9pt 12pt; margin: 8pt 0 10pt; break-inside: avoid; }}
.box.warn {{ background: #fef1d5; }}
.box.ok {{ background: #e6efda; }}
.box b.k {{ color: #5f6b45; }}
ol, ul {{ margin: 0 0 8pt 16pt; padding: 0; }}
li {{ margin: 0 0 4pt; }}
code, .f {{ font-family: Menlo, Consolas, monospace; font-size: 8.4pt; }}
.shot {{ width: 100%; border-radius: 6pt; border: 1px solid #e4e4e4; }}
.two {{ display: flex; gap: 10pt; }} .two > div {{ flex: 1; }}
.cap {{ font-size: 8.5pt; color: #636369; margin-top: 2pt; }}
table.t {{ width: 100%; border-collapse: collapse; font-size: 7.4pt; line-height: 1.35; margin-top: 6pt; }}
table.t th {{ text-align: left; font-weight: 600; color: #636369; text-transform: uppercase; letter-spacing: .04em; font-size: 6.6pt; border-bottom: 1px solid #c8c8c8; padding: 3pt 3pt; }}
table.t td {{ border-bottom: 1px solid #ececec; padding: 3pt 3pt; vertical-align: top; }}
table.t td.n {{ font-variant-numeric: tabular-nums; white-space: nowrap; text-align: right; }}
table.t td.s {{ color: #4a4a4f; }}
table.t td.f {{ font-size: 6.6pt; word-break: break-all; }}
table.t tr {{ break-inside: avoid; }}
.toc li {{ margin-bottom: 2pt; }}
.tree {{ font-family: Menlo, Consolas, monospace; font-size: 8.4pt; background: #f2f2f2; border-radius: 8pt; padding: 10pt 12pt; white-space: pre; line-height: 1.5; }}
.step {{ display: inline-block; background: #859369; color: #1c1c20; font-weight: 700; border-radius: 99pt; padding: 0 7pt; font-size: 9pt; margin-right: 4pt; }}
"""
    screens_html = []
    for S in SCREENS:
        p1, p2 = S["previews"]
        th = S["themes"]
        screens_html.append(f"""
<section class="page">
  <div class="eyebrow">Screen {S['key']} · folder “3 - Screens/{esc(S['folder'])}”</div>
  <h2>{esc(S['title'])}</h2>
  <p>{esc(S['blurb'])}</p>
  <div class="two"><div><img class="shot" src="{prev(p1)}"><div class="cap">{th[0].title()} (preview with sample values)</div></div>
  <div><img class="shot" src="{prev(p2)}"><div class="cap">{th[1].title()}</div></div></div>
  <p class="cap">Build it top to bottom. X/Y are the top-left corner in screen pixels; “X size/Y size” are the component's width and height. The same table is in the folder's <code>…_components.csv</code>. Every file starts with the screen's name (for example <code>diagnostic_background_dark.png</code>).</p>
  {table(S['rows'])}
</section>""")
    body = f"""
<section class="cover">
  <div class="eyebrow">Classic Mini DIY · Haltech iC-7 · NSP</div>
  <h1>Bad Wolf iC-7 Dash<br>Install Guide</h1>
  <p class="lede">Everything you need to put the Bad Wolf screens on your iC-7: the images, needles, lamps and fonts, plus where each piece goes. You build each screen once in NSP; after that it lives in your dash map like any Haltech screen.</p>
  <img src="{splash}">
  <h3>What's in this guide</h3>
  <ol class="toc">
    <li>How custom screens work in NSP (and why the gauges are "empty")</li>
    <li>Before you start: back up, versions, which five screens</li>
    <li>What's in the bundle</li>
    <li>Fonts and splash screen</li>
    <li>The build method, once, in detail (with needle calibration)</li>
    <li>One page per screen: every component, position and setting</li>
    <li>Empty versions: blank layouts you can fill with any channel, any time</li>
    <li>Write to the dash, day/night, troubleshooting</li>
  </ol>
</section>

<section class="page">
  <div class="eyebrow">Part 1</div>
  <h2>How custom screens work in NSP</h2>
  <p>Since NSP 2.30, the iC-7 screens are fully editable. A screen is a stack of <b>components</b> you add with right-click › <b>Add Component</b>: <b>Images</b>, <b>Numeric Gauges</b>, <b>Dial Gauges</b>, bars and <b>Indicators</b>. Each has X, Y and Z position, a size, a channel and colours. Z is the layer: 0 is the back.</p>
  <p>You were right that the gauges need to be "empty". Here is how this bundle does it:</p>
  <ol>
    <li><b>Everything that never moves is one picture.</b> The faces, numbers, ticks, chrome, tiles and labels are all printed into one 860 × 480 <b>background image</b>, placed as an Image component on the bottom layer.</li>
    <li><b>NSP draws only the moving parts on top.</b> Each needle is a Dial Gauge with its own dial made invisible (every palette colour set to opacity 0) and our needle image loaded as its <b>Needle Image Source</b>. Numbers are Numeric Gauges with only the value showing.</li>
    <li><b>Bars, lamps and status pills go underneath.</b> Wherever one lives, the background has a see-through cut-out: a rounded slot for a bar, a round lens or an arrow for a lamp, a pill shape for a status light (its label stays printed on top). A plain NSP component sits below the background and shows through, so the artwork gives it its shape and the component stays generic: a bar, or an indicator that is just a block of colour switching between its off and on colours.</li>
  </ol>
  <p>This is the same method Haltech shows in its "Import Custom Screens and Needles" video: needle PNGs with a transparent background, <b>pointing straight up</b>, set with Needle Image Source and Needle Image Offset; and a dial gauge's palette opacities set to zero so only the needle shows.</p>
  <div class="box ok"><b>Two versions of every screen.</b> <b>Printed</b> (Parts 5 and 6): labels, units and scales are part of the artwork, so you only add needles and numbers. It's the quickest build and looks exactly like the previews, but changing what a gauge shows means new artwork. <b>Empty</b> (Part 7): only the hardware is in the picture (chrome, blank faces, plates, windows, tiles). NSP draws the ticks, numbers, labels and units, so you can swap any slot to any channel later without a redesign.</div>
  <div class="box"><b class="k">Screen size.</b> The iC-7 layout canvas in NSP is <b>860 × 480</b>. Your own Bad Wolf dash map uses an 860 × 480 layout and splash, so every file here is made at exactly that size. Coordinates in this guide are screen pixels from the top-left corner.</div>
  <div class="box warn"><b>Honest note.</b> Haltech hasn't published written specs for the editor. Field names below are taken from Haltech's own tutorial videos, and they may differ slightly in your NSP version. Where something can't be known in advance (mainly how NSP scales a needle image), Part 5 has a one-time, two-minute calibration.</div>

</section>

<section class="page">
  <div class="eyebrow">Part 2</div>
  <h2>Before you start</h2>
  <ol>
    <li><b>Back up your current dash map.</b> Go online with the dash and save the dash map to a new file (your last one in the repo is <code>badwolf.ic7-2-34-0.nexmap</code>). If anything goes sideways, write that back.</li>
    <li><b>NSP 2.30 or newer</b> on the PC, and the dash updated to match. Your map is already 2.34, so you're set.</li>
    <li><b>Copy this whole folder to the Windows machine that runs NSP</b> (or open it from the VM's shared folder). NSP will ask for each file as you go.</li>
    <li><b>Pick five screens.</b> The dash holds up to five. A good set: <b>A Classic</b> · <b>B Tuning</b> (or C Six-pack / D Hybrid) · <b>E Diagnostic</b> · <b>F Diagnostic Dense</b> · plus your favourite of the rest.</li>
    <li><b>Channel names.</b> Channels below come from your October 2026 IO report. NSP's channel picker may word them a little differently; pick the closest match.</li>
  </ol>
  <div class="box ok"><b>Tip.</b> Build one screen on its own first (Classic is a good start), write it to the dash, and check it in the car before doing the rest. Once the first needle is calibrated, the rest go quickly.</div>

  <div class="eyebrow" style="margin-top:14pt">Part 3</div>
  <h2>What's in the bundle</h2>
  <div class="tree">Bad Wolf iC-7 Dash/
├─ Install Guide - Bad Wolf iC-7 Dash.pdf      ← this file
├─ 1 - Fonts/                 Outfit + Barlow Condensed (.ttf), licence note
├─ 2 - Splash Screen/         Plate (recommended), Dial, Car · 860×480
├─ 3 - Screens/
│  ├─ A - Classic/            classic_background_day/night, needles, lamps, classic_components.csv
│  ├─ B - Tuning/             AFR + target needle, oil T, fuel P, volts, air T
│  ├─ C - Six-pack/           six equal gauges
│  ├─ D - Hybrid/             big AFR + six data plates
│  ├─ E - Diagnostic/         diagnostic_background_dark/light, indicator fill
│  └─ F - Diagnostic Dense/   diagnostic_dense_background_dark/light, indicator fill
│     each folder also has "Previews (not for import)"
│     and "Empty version/": blank background(s) + …_slots_empty.csv
│     every file is named after its screen: tuning_needle_large_day.png…
└─ 4 - Reference/             layout spec (JSON), alternate needles, generator source</div>
  <p>Every screen folder holds only what that screen needs. Files ending <b>_Day / _Night</b> (or <b>_Dark / _Light</b>) are the two looks; build one, or both as separate screens. Lamp files come in colour and as <b>_white</b> masks (see Part 5, Indicators).</p>

  <div class="eyebrow page">Part 4</div>
  <h2>Fonts and splash screen</h2>
  <h3><span class="step">1</span>Fonts</h3>
  <p>NSP lets you upload your own font from a text component's <b>Font Source</b>. The first time a component needs Outfit or Barlow Condensed, choose <b>upload</b> and pick the .ttf from <b>1 - Fonts</b>; after that it's in the list.</p>
  <ul><li><b>Outfit SemiBold</b>: values on the Diagnostic screens.</li><li><b>Outfit Medium</b>: small secondary values (TGT, PW, PEDAL…).</li><li><b>Barlow Condensed SemiBold</b>: odometer, LCD readouts and Hybrid data plates.</li></ul>
  <p>If you'd also like them on the PC for previews, double-click each .ttf and choose Install. That's optional.</p>
  <h3><span class="step">2</span>Splash screen</h3>
  <p>In the NSP tree under your iC-7, open <b>Splash Screen</b> and set its image to <code>splash_bad_wolf_plate.png</code> (recommended; or the dial or car version). They are 860 × 480, the same size as your current hero image.</p>
</section>

<section>
  <div class="eyebrow" style="margin-top:16pt">Part 5</div>
  <h2>The build method</h2>
  <p>Every screen is built the same way. Do this once slowly; the per-screen tables then only give positions and settings.</p>
  <h3><span class="step">1</span>Add a blank screen</h3>
  <p>In the tree go to <b>Screens</b> › <b>+ Add Screen</b> › <b>Blank Screen</b>. Rename it (for example "Classic").</p>
  <h3><span class="step">2</span>Background (Z 1)</h3>
  <p>Right-click the empty screen › <b>Add Component</b> › <b>Images</b> › Image. Set <b>Image Source</b> to the screen's <code>…_background_….png</code>. Set X 0, Y 0, X size 860, Y size 480, Z 1. The bars go underneath it (Z 0); everything else sits on top.</p>
  <h3><span class="step">3</span>Needles: a Dial Gauge with an invisible dial</h3>
  <ol>
    <li>Add Component › <b>Dial Gauges</b> › the retro circular gauge.</li>
    <li>Type X, Y, X size and Y size from the table. The box is a square whose centre is the gauge's pivot.</li>
    <li><b>Channel</b>: from the table. <b>Min / Max</b>: from the table (Display Min / Display Max).</li>
    <li><b>Gauge Start Angle −135</b> and <b>Gauge End Angle 135</b> for every gauge (0° is straight up, so −90 is flat left and +90 is flat right).</li>
    <li><b>Needle Image Source</b> › Choose File › the <code>…_needle_….png</code> from the folder. Each one is a tight, narrow strip pointing straight up, with no empty space around it.</li>
    <li><b>Palette Colours</b>: set the opacity of every colour to 0 (numbers, ticks, arc, warning, centre, background) <b>except the Needle</b>. Turn tick counts to 0 if your version shows them anyway.</li>
    <li><b>Needle Image Offset −80%</b>. Every needle's pivot sits exactly 80% of the way down its image, above a short counterweight tail.</li>
    <li>Add the <b>hub</b> (<code>…_hub_….png</code>) as an Image component on top (Z 5), centred on the pivot (positions in the table). It's round, so it never needs to turn.</li>
  </ol>
  <div class="box"><b class="k">Why the needles changed, and checking the first one.</b> NSP sizes and places a needle image from its own outline. The first version of these needles was drawn on large square images with lots of empty space, so they could never be offset to pivot properly. The needles are now tight strips (for example 14 × 212 px for the large needle), with the boss moved to a separate hub image.
  <ul style="margin-top:4pt">
    <li>Turn on <b>Simulation</b> and sweep the value. With −80% the needle should turn about the hub. If it's still a little off, nudge the offset by 1–2%.</li>
    <li>If your NSP measures the offset differently and −80% isn't close, try the <b>no-tail</b> needles in <code>4 - Reference/Alternate needles</code>. Their pivot is exactly on the bottom edge, so the offset is 0%.</li>
    <li>Length: if the tip falls short of or past the ticks, tick <b>Override Scaling</b> if your version shows it, or change the gauge's X/Y size equally, keeping the centre.</li>
  </ul></div>
  <h3><span class="step">4</span>Numbers: Numeric Gauge, value only</h3>
  <p>Add Component › <b>Numeric Gauges</b>. Set position, size and channel from the table. Hide the label and units text (opacity 0, or delete the text), then set the value's font, size, colour and alignment as listed. Units are already printed on the background.</p>
  <h3><span class="step">5</span>Bars</h3>
  <p>Bars go <b>behind</b> the background. Every place a bar lives has a see-through slot cut into the background image, with rounded ends. Put NSP's horizontal bar component under it (Z 0), at the position in the table or a few pixels larger on every side. The background then masks it, so the bar takes the slot's exact shape and the bar itself can stay plain and generic.</p>
  <ul><li><b>Fill colour</b>: as listed (olive on the diagnostic screens, ink or orange on the classic windows and plates).</li>
  <li><b>Background colour</b>: the empty-track colour listed. It shows through the part of the slot the fill hasn't reached.</li>
  <li>Frame, border and any text on the bar: opacity 0.</li></ul>
  <p>A slot with no bar behind it shows the screen's black, so give every slot a bar, or a plain bar fixed at 0 as a filler.</p>
  <h3><span class="step">6</span>Indicators: lamps and status pills (behind, like the bars)</h3>
  <p>Lamps and pills work exactly like the bars. Each lamp (round lens or turn arrow) and each status pill is a see-through cut-out in the background. The pill labels are printed on the background, on top.</p>
  <ul><li>Add Component › <b>Indicator</b> at Z 0 (under the background), sized to the box in the table, which is the cut-out plus a small margin.</li>
  <li><b>Image Source</b>: <code>…_indicator_fill_white.png</code>, a plain white square, so the indicator is just a block of colour. (If your NSP's indicator can show a plain colour without an image, that works too.)</li>
  <li><b>Off colour</b>: the unlit colour from the table (dark lens, faint arrow, dim pill). <b>On colour</b>: the lamp or status colour. NSP switches between them and the cut-out shapes the result.</li>
  <li>Every cut-out needs something behind it, or it shows the screen's black.</li></ul>
  <h3><span class="step">7</span>Layers</h3>
  <p><b>Z 0: bars, lamps and pills</b> (under the background) · <b>Z 1: background</b> · Z 2: numbers · Z 3: secondary needles · Z 4: main needles · Z 5: hubs. Higher numbers draw on top.</p>
</section>
{''.join(screens_html)}
{empty_html()}
<section class="page">
  <div class="eyebrow">Part 8</div>
  <h2>Write to the dash, day/night, troubleshooting</h2>
  <h3>Order and write</h3>
  <ol>
    <li>In <b>Screens</b>, drag the screens into the order you want (up to five), and choose which one the dash starts on.</li>
    <li>Set up the screen buttons if you haven't (one button cycling, or next/previous).</li>
    <li>Write the dash map to the dash, then save the dash map to a new file.</li>
  </ol>
  <h3>Day and night</h3>
  <p>NSP's day/night setting switches colours, not background images. Two easy ways to use the night artwork: build the night version as its own screen (Classic · Night next to Classic · Day), or keep one screen and swap …_background_day for …_background_night and the needles for their _night versions (and the indicator off colours for their night values). The night needles are orange so they read on the dark faces.</p>
  <h3>Moving a finished screen into another dash map</h3>
  <p>From Haltech's video: open the dash map that holds the screen, add blank screens until it sits in the slot you want, then save. Open your main map and use <b>File › Import and upload</b>, pick that file, tick <b>import screens</b>, choose the screen and <b>import the selected items</b>. This adds screens without wiping the others.</p>
  <h3>If something looks off</h3>
  <ul>
    <li><b>Needle swings around the wrong point:</b> change Needle Image Offset (Part 5).</li>
    <li><b>Needle lines up at one end but not the other:</b> check Min/Max and that Start/End are −135/135. The boost gauge is linear from −9.82 to 30 psi.</li>
    <li><b>Numbers sit a few pixels off:</b> numeric gauges pad their text slightly differently by version. Nudge Y by eye with Simulation on.</li>
    <li><b>A whole dial shows up behind our face:</b> a palette colour still has opacity above 0.</li>
    <li><b>Everything is offset or scaled:</b> make sure the background image is X 0, Y 0, 860 × 480.</li>
    <li><b>Starting warning colours</b> (set to your engine): coolant over 100 °C, oil under 15 psi above 2000 rpm, oil temp over 120 °C, battery under 12.5 V running, boost at your limit. Use NSP's Warning Min/Max so values turn orange or red.</li>
  </ul>
  <div class="box"><b class="k">Changing the artwork.</b> Ranges, the 7000 rpm redline and labels are set in <code>4 - Reference/Generator source</code>. Change a value and re-run to make new PNGs at the same positions.</div>
  <p class="cap" style="margin-top:14pt">Classic Mini DIY by Cole Gentry. Fonts: Outfit and Barlow Condensed, SIL Open Font License. Method references: Haltech, "How To Customise Your Haltech Dash" and "Tips and Tricks: How to Import Custom Screens and Needles" (YouTube).</p>
</section>"""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"


# ------------------------------------------------------------------ EMPTY versions
EMPTY_DIR = SRC / "empty"
EMPTY_SLOTS = json.loads((EMPTY_DIR / "empty_slots.json").read_text()) if (EMPTY_DIR / "empty_slots.json").exists() else {}
EMPTY_FOR = {"A": "five_gauge", "B": "five_gauge", "C": "six_pack", "D": "hybrid", "E": "diagnostic", "F": "diagnostic_dense"}
EMPTY_TITLE = {"five_gauge": "Five-gauge (screens A and B)", "six_pack": "Six-pack (screen C)", "hybrid": "Hybrid (screen D)",
               "diagnostic": "Diagnostic, 12 tiles (screen E)", "diagnostic_dense": "Diagnostic Dense, 20 tiles (screen F)"}
EMPTY_THEMES = {"five_gauge": ("day", "night"), "six_pack": ("day", "night"), "hybrid": ("day", "night"),
                "diagnostic": ("dark", "light"), "diagnostic_dense": ("dark", "light")}


def printed_contents(layout):
    """What each slot holds in the printed version, so it can be rebuilt or swapped."""
    if layout == "five_gauge":
        return {"Centre": "A: Speedo 10–130 mph · B: Air/fuel 10–20 AFR",
                "Centre · LCD window": "A: Odometer + trip · B: AFR + target",
                "Centre · lower window": "A: Fuel level bar · B: Throttle position bar",
                "Top left": "A: Oil pressure 0–100 psi · B: Oil temp 50–150 °C",
                "Bottom left": "A: Water 30–110 °C · B: Fuel pressure 0–80 psi",
                "Top right": "A: Tacho 0–8000 rpm · B: Volts 8–16 V",
                "Bottom right": "A: Boost −9.8–30 psi · B: Intake air 0–100 °C"}
    if layout == "six_pack":
        return dict(zip(["Top left", "Top centre", "Top right", "Bottom left", "Bottom centre", "Bottom right"],
                        ["Air/fuel 10–20 AFR", "Oil temp 50–150 °C", "Fuel pressure 0–80 psi", "Intake air 0–100 °C",
                         "Volts 8–16 V", "Ignition −10–50 °BTDC"]))
    if layout == "hybrid":
        d = {"Left dial": "Air/fuel 10–20 AFR (+ target needle)", "Left dial · LCD window": "AFR + target",
             "Left dial · lower window": "Throttle position bar"}
        for i, (pid, lab, unit, lo, hi, dec) in enumerate(gen2.PLATES, 1):
            d[f"Plate {i}"] = f"{lab} {lo}–{hi} {unit}"
        return d
    if layout == "diagnostic":
        d = {"Top 1 (wide-ish)": "RPM value", "Top 2 (long, for a bar)": "RPM bar 0–8000", "Top 3": "Speed (mph)"}
        for i, t in enumerate(gen.DIAG_TILES, 1):
            d[f"Tile {i} (row {(i - 1) // 4 + 1}, col {(i - 1) % 4 + 1})"] = f"{t[1]} {t[4]}–{t[5]} {t[2]}"
        d["Status strip"] = "Status lamps + labels, fuel, boost trim"
        return d
    if layout == "diagnostic_dense":
        d = {"Top 1": "RPM value", "Top 2 (long, for a bar)": "RPM bar 0–8000", "Top 3": "Speed (mph)"}
        for i, t in enumerate(gen2.DENSE, 1):
            d[f"Tile {i} (row {(i - 1) // 5 + 1}, col {(i - 1) % 5 + 1})"] = f"{t[1]} {t[4]}–{t[5]} {t[2]}"
        d["Status strip"] = "Status lamps + labels, fuel, boost trim"
        return d
    return {}


def slot_rows(layout):
    pc = printed_contents(layout)
    rows = []
    for s in EMPTY_SLOTS[layout]:
        b = s["box"]
        centre = f"{s['cx']}, {s['cy']}" if "cx" in s else f"{b['x'] + b['w'] // 2}, {b['y'] + b['h'] // 2}"
        rows.append(dict(slot=s["slot"], kind=s["kind"], x=b["x"], y=b["y"], w=b["w"], h=b["h"], centre=centre,
                         printed=pc.get(s["slot"], "—")))
    return rows


def status_dot():
    r = gen.Renderer()
    p = ROOT / "out" / "_white" / "Status_Dot_white.png"
    r.render(gen.svg(16, 16, '<circle cx="8" cy="8" r="7" fill="#ffffff"/>'), 16, 16, p)
    r.close()
    return p


def add_empty(white):
    dot = status_dot()
    scr = B / "3 - Screens"
    for S in SCREENS:
        layout = EMPTY_FOR[S["key"]]
        d = scr / S["folder"] / "Empty version"
        d.mkdir(parents=True)
        for th in EMPTY_THEMES[layout]:
            shutil.copy(EMPTY_DIR / f"{layout}/{layout}_empty_{th}.png", d / nm(S, f"background_{th}_empty.png"))
        if layout.startswith("diagnostic"):
            shutil.copy(dot, d / nm(S, "status_dot_white.png"))
        else:
            for lid in ("lamp_hb", "lamp_ign", "lamp_oil", "lamp_cel", "lamp_fan", "lamp_turn_left", "lamp_turn_right", "lamp_knock", "lamp_log"):
                shutil.copy(white[lid], d / nm(S, f"{LAMP_NAME[lid]}_white.png"))
        with open(d / nm(S, "slots_empty.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Slot", "Kind", "X", "Y", "X size", "Y size", "Centre", "In the printed version"])
            for r in slot_rows(layout):
                w.writerow([r["slot"], r["kind"], r["x"], r["y"], r["w"], r["h"], r["centre"], r["printed"]])
        (d / nm(S, "empty_readme.txt")).write_text(
            "Empty version: hardware only (chrome, blank faces, plates, windows, tiles).\n"
            "No labels, units, numbers, ticks or scales are printed, so any slot can show any channel.\n"
            f"Bars go BEHIND this background: the see-through slots in it shape them.\n"
            f"Needles are the {SLUG[S['key']]}_needle_*.png files in the folder above. Build steps: Part 7 of the Install Guide.\n"
            f"{nm(S, 'slots_empty.csv')} lists every slot's position and size, and what the printed version puts there.\n")


def empty_html():
    def tbl(rows):
        out = ['<table class="t"><thead><tr><th>Slot</th><th>Kind</th><th>X</th><th>Y</th><th>X size</th><th>Y size</th>'
               '<th>Centre</th><th>In the printed version</th></tr></thead><tbody>']
        for r in rows:
            out.append(f'<tr><td><b>{esc(r["slot"])}</b></td><td>{esc(r["kind"])}</td><td class="n">{r["x"]}</td><td class="n">{r["y"]}</td>'
                       f'<td class="n">{r["w"]}</td><td class="n">{r["h"]}</td><td class="n">{r["centre"]}</td><td class="s">{esc(r["printed"])}</td></tr>')
        out.append("</tbody></table>")
        return "".join(out)

    pages = []
    for layout in ("five_gauge", "six_pack", "hybrid", "diagnostic", "diagnostic_dense"):
        t1, t2 = EMPTY_THEMES[layout]
        img = lambda th: (EMPTY_DIR / f"{layout}/{layout}_empty_{th}.png").as_uri()
        pages.append(f"""
<section class="page">
  <div class="eyebrow">Part 7 · Empty layout</div>
  <h2>{esc(EMPTY_TITLE[layout])}</h2>
  <div class="two"><div><img class="shot" src="{img(t1)}"><div class="cap">…_background_{t1}_empty.png</div></div>
  <div><img class="shot" src="{img(t2)}"><div class="cap">…_background_{t2}_empty.png</div></div></div>
  <p class="cap">Each slot's box is where the component goes. For dials, the box is the face (centre = pivot). The last column says what the printed version puts there, if you want to start from that and change things.</p>
  {tbl(slot_rows(layout))}
</section>""")
    return f"""
<section class="page">
  <div class="eyebrow">Part 7</div>
  <h2>Empty versions: change what any slot shows</h2>
  <p>Every screen folder has an <b>Empty version</b> subfolder holding a background with only the hardware: chrome bezels, blank magnolia faces, data plates, the LCD and lower windows, or plain tiles. There are no labels, units, numbers, ticks, scales or lamps in the picture. NSP draws all of those, so a slot can show oil temp today and EGT next year with no new artwork.</p>
  <p>It's the same build as Parts 5–6 with one difference: you <b>keep</b> the parts of each NSP component that the printed art used to cover, and style them to match.</p>

  <h3><span class="step">1</span>Background</h3>
  <p>Image component, <code>…_background_…_empty.png</code>, X 0, Y 0, 860 × 480, Z 1. The empty backgrounds keep the same see-through bar slots as the printed ones (bottom of every tile and plate, the lower window, the long top tile), so bars go underneath at Z 0, exactly as in Part 5.</p>

  <h3><span class="step">2</span>Dials on an empty face</h3>
  <ol>
    <li>Dial Gauge (retro circular) with its box set to the slot's box from the table. The box is the face, so ticks and numbers land on it.</li>
    <li>Channel, Min/Max of your choice; Start −135°, End 135°. <b>Label Text</b>: what the gauge shows ("OIL", "EGT"…).</li>
    <li><b>Palette Colours</b>: ticks, numbers and label in the ink colour below, opacity 100%. Arc, background and centre at opacity 0. Use the warning colour for your redline or limit zone (Warning Min/Max).</li>
    <li>Number font <b>Barlow Condensed SemiBold</b>; label font <b>Outfit Bold</b>. Choose major/minor tick counts so labels land on round numbers (0–100 → 5 majors; 0–8000 → 8 majors).</li>
    <li>Needle: the same needle files as the printed screens (<code>…_needle_large</code> for the big faces, <code>…_needle_small</code> for 160 px faces, <code>sixpack_needle_medium</code> for the six-pack's 200 px faces), with the same −80% offset and a hub on top. If NSP draws the needle to the box size, it will now reach the tick ring by default.</li>
    <li>If NSP's ticks sit too close to the chrome, shrink the box a few pixels on each side and keep the same centre.</li>
  </ol>

  <h3><span class="step">3</span>Windows, plates and tiles</h3>
  <ul>
    <li><b>LCD window</b> (76 × 36): two value-only Numeric Gauges stacked (each 17 px tall), Barlow Condensed SemiBold 15 px, <code>#E9E04A</code> day / <code>#C9C03C</code> night. Or one larger value.</li>
    <li><b>Lower window</b> (104 × 26): its bar slot (88 × 5) takes a bar from underneath. The top of the window is free for a small label.</li>
    <li><b>Data plates</b> and <b>tiles</b>: one Numeric Gauge filling the slot with its <b>label</b> and <b>units</b> switched on. Plates: label Outfit Bold 12 px in ink, units Outfit SemiBold 10 px, value Barlow Condensed SemiBold ~54 px. Tiles: label Outfit SemiBold 11 px, units Outfit Medium 11 px, value Outfit SemiBold 38 px (12-tile) or 32 px (20-tile). Each one has a bar slot along the bottom: put a bar under it, or a plain bar at 0 so the slot shows the track colour.</li>
  </ul>

  <h3><span class="step">4</span>Lamps and status lights anywhere</h3>
  <p>The empty backgrounds have no lamp or pill cut-outs, because where a lamp goes is up to you. To place one anywhere, put the Indicator <b>on top</b> of the background instead (Z 2) and give it both states. Use a <code>…_lamp_…_white.png</code> (classic screens) or <code>…_status_dot_white.png</code> (diagnostic) as the image. Set the <b>On</b> colour to the lamp colour and the <b>Off</b> colour to the "lamp off" colour below, so it reads as a dark lens until it lights. On the diagnostic screens, put a text label beside each dot in the status strip.</p>

  <table class="t" style="margin-top:8pt"><thead><tr><th>Colour role</th><th>Classic day</th><th>Classic night</th><th>Diagnostic dark</th><th>Diagnostic light</th></tr></thead><tbody>
    <tr><td><b>Ink</b> (ticks, numbers, values)</td><td><code>#1D1B18</code></td><td><code>#E9E2CC</code></td><td><code>#E4E4E7</code></td><td><code>#18181B</code></td></tr>
    <tr><td><b>Secondary</b> (labels, units)</td><td><code>#3A362F</code></td><td><code>#B9B19B</code></td><td><code>#B6B6BC</code> / units <code>#9A9AA1</code></td><td><code>#4A4A4F</code> / units <code>#636369</code></td></tr>
    <tr><td><b>Warning / redline</b></td><td><code>#ED7135</code></td><td><code>#F08A54</code></td><td><code>#F08A54</code></td><td><code>#ED7135</code></td></tr>
    <tr><td><b>Danger</b></td><td><code>#B22222</code></td><td><code>#EF7676</code></td><td><code>#EF7676</code></td><td><code>#B22222</code></td></tr>
    <tr><td><b>Bar fill</b></td><td><code>#1D1B18</code></td><td><code>#F08A54</code></td><td><code>#9AAC7F</code></td><td><code>#859369</code></td></tr>
    <tr><td><b>Bar track</b> (bar background colour)</td><td><code>#D6CDB4</code> windows · <code>#CCC5B3</code> plates</td><td><code>#1D1C19</code> windows · <code>#403D37</code> plates</td><td><code>#333337</code></td><td><code>#EBEBEB</code></td></tr>
    <tr><td><b>Lamp off</b></td><td><code>#2A2620</code></td><td><code>#0D0C0B</code></td><td><code>#2A2A30</code></td><td><code>#E4E4E4</code></td></tr>
    <tr><td><b>Needle</b></td><td>black (Day files)</td><td>orange (Night files)</td><td>—</td><td>—</td></tr>
  </tbody></table>
  <div class="box"><b class="k">Mixing the two.</b> You can start from the printed screen and later rebuild just one gauge as "empty": keep the printed background, put a blank face image over that slot (crop it from the empty background), and add NSP ticks there. In practice it's quicker to switch the whole screen to the empty background once you start customising.</div>
</section>
{''.join(pages)}"""


def main():
    white = white_lamps()
    classic_screens()
    tuning_like("B", "B - Tuning", "Classic · Tuning", "classic_tuning", "classic_tuning",
                "What the analog gauges don't show: a big air/fuel gauge with lambda ring and target needle, oil temp, fuel pressure, volts and intake air, plus throttle position, knock and logging lamps.",
                ["speedo", "small", "target"])
    tuning_like("C", "C - Six-pack", "Classic · Six-pack", "classic_sixpack", "classic_sixpack",
                "Six equal gauges, the easiest to read at a glance: AFR, oil temp, fuel pressure, intake air, volts and ignition timing.",
                ["medium"])
    tuning_like("D", "D - Hybrid", "Classic · Hybrid", "classic_hybrid", "classic_hybrid",
                "The big AFR gauge plus six magnolia data plates with large numbers: oil temp, fuel pressure, air temp, battery, ignition and injector duty.",
                ["speedo", "target"])
    diag_screen("E", "E - Diagnostic", "Diagnostic", "diagnostic", "diagnostic",
                "Twelve tiles for dyno days and fault-finding, an RPM bar with redline, and status pills that light from behind.")
    diag_screen("F", "F - Diagnostic Dense", "Diagnostic · Dense", "diagnostic_dense", "diagnostic_dense",
                "Twenty tiles in four themed rows: boost and fuelling, spark and injection, temperatures and pressures, driver inputs and electrics.")
    for S in SCREENS:
        finish(S)
    assemble(white)
    add_empty(white)
    html_path = ROOT / "out" / "_guide.html"
    html_path.write_text(guide_html())
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page()
        pg.goto(html_path.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(500)
        pg.pdf(path=str(B / "Install Guide - Bad Wolf iC-7 Dash.pdf"), format="Letter", print_background=True,
               display_header_footer=True, header_template="<span></span>",
               footer_template="<div style='font-size:7pt;color:#9a9aa1;width:100%;text-align:center;font-family:sans-serif'>Bad Wolf iC-7 Dash · <span class='pageNumber'></span> / <span class='totalPages'></span></div>",
               margin=dict(top="0.55in", bottom="0.6in", left="0.55in", right="0.55in"))
        br.close()
    print("bundle at", B)


if __name__ == "__main__":
    main()
