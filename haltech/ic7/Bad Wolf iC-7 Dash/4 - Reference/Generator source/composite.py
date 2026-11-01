"""Composite preview: background + rotated needles + lit lamps + sample text, from the spec JSON."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import sys as _s; _s.path.insert(0, str(Path(__file__).resolve().parent)); from holes import underlay

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "out" / "Haltech-iC7-CMDIY"
spec = json.loads((P / "nsp_layout_spec.json").read_text())
F = ROOT / "fonts"

SAMPLE = {"speedo": 47, "tacho": 3150, "oil": 58, "water": 86, "boost": 4.5}
LIT = ["lamp_ign", "lamp_turn_right", "lamp_cel"]


def classic(theme):
    bg = underlay(P / f"classic/{theme}/classic_background_{theme}.png", lit=LIT)
    g = spec["classic"]["gauges"]
    nmap = {"speedo": "speedo", "tacho": "tacho", "oil": "small", "water": "small", "boost": "small"}
    for gid, v in SAMPLE.items():
        s = g[gid]
        a = s["start_angle_deg"] + (v - s["display_min"]) / (s["display_max"] - s["display_min"]) * s["sweep_deg"]
        name = nmap[gid]
        npath = next((P / f"classic/{theme}/needles").glob(f"needle_{name}_{theme}_up_*px.png"))
        if gid == "tacho":
            tpath = next((P / f"classic/{theme}/needles").glob(f"needle_telltale_{theme}_up_*px.png"))
            tl = Image.open(tpath).rotate(-(s["start_angle_deg"] + 6800 / 8000 * 270), resample=Image.BICUBIC)
            bg.alpha_composite(tl, (s["pivot_x"] - tl.width // 2, s["pivot_y"] - tl.height // 2))
        n = Image.open(npath).rotate(-a, resample=Image.BICUBIC)
        bg.alpha_composite(n, (s["pivot_x"] - n.width // 2, s["pivot_y"] - n.height // 2))
    d = ImageDraw.Draw(bg)
    fnt = ImageFont.truetype(str(F / "BarlowCondensed-600.ttf"), 15)
    for key, val in (("odometer", "951"), ("trip", "951.7")):
        t = spec["classic"]["text"][key]
        d.text((t["x"] + t["w"], t["y"] + t["h"] / 2), val, font=fnt, fill=t["color"], anchor="rm")
    fb = spec["classic"]["fuel_bar"]
    col = fb["color"] if theme == "day" else fb["night_color"]
    d.rounded_rectangle((fb["x"], fb["y"], fb["x"] + int(fb["w"] * 0.5), fb["y"] + fb["h"]), radius=2, fill=col)
    return bg


def diag(theme):
    bg = underlay(P / f"diagnostic/{theme}/diagnostic_background_{theme}.png", lit=("pill_fan", "pill_pump", "pill_log"))
    d = ImageDraw.Draw(bg)
    vals = {"rpm_value": "3150", "speed_value": "47", "boost_value": "4.5", "boost_tgt": "12.0", "boost_wg": "38%",
            "afr_value": "13.2", "afr_tgt": "12.8", "ign_value": "24.5", "inj_value": "41", "inj_pw": "6.8",
            "clt_value": "86", "oilp_value": "58", "oilt_value": "97", "fuelp_value": "43.5", "iat_value": "31",
            "batt_value": "14.1", "tps_value": "62", "tps_pedal": "64", "knock_value": "3", "knock_ret": "0.0",
            "fuel_value": "52", "trim_value": "2"}
    fracs = {"rpm_bar": 3150 / 8000, "boost_bar": (4.5 + 10) / 40, "afr_bar": .32, "ign_bar": 34.5 / 60, "inj_bar": .41,
             "clt_bar": 56 / 90, "oilp_bar": .58, "oilt_bar": 67 / 120, "fuelp_bar": 43.5 / 80, "iat_bar": 41 / 90,
             "batt_bar": 4.1 / 6, "tps_bar": .62, "knock_bar": .03}
    for c in spec["diagnostic"][theme]:
        if c["type"].startswith("Text") and c["id"] in vals:
            size = c["size"]
            fn = "Outfit-600.ttf" if "Semi" in c["font"] else "Outfit-500.ttf"
            fnt = ImageFont.truetype(str(F / fn), size)
            if c["align"] == "right":
                d.text((c["x"] + c["w"], c["y"] + c["h"] / 2), vals[c["id"]], font=fnt, fill=c["color"], anchor="rm")
            else:
                d.text((c["x"], c["y"] + c["h"] / 2), vals[c["id"]], font=fnt, fill=c["color"], anchor="lm")
        elif c["type"].startswith("Bar") and c["id"] in fracs:
            d.rounded_rectangle((c["x"], c["y"], c["x"] + int(c["w"] * fracs[c["id"]]), c["y"] + c["h"]),
                                radius=min(4, c["h"] // 2), fill=c["color"])
    return bg


if __name__ == "__main__":
    out = ROOT / "out" / "Haltech-iC7-CMDIY" / "previews"
    out.mkdir(exist_ok=True)
    for th in ("day", "night"):
        classic(th).save(out / f"preview_classic_{th}.png")
    for th in ("dark", "light"):
        diag(th).save(out / f"preview_diagnostic_{th}.png")
    print("ok")
