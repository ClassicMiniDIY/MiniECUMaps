"""Previews for the round-2 screens (needles, lamps and sample values in place)."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import sys as _s; _s.path.insert(0, str(Path(__file__).resolve().parent)); from holes import underlay

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "out" / "Haltech-iC7-CMDIY"
F = ROOT / "fonts"
spec = json.loads((P / "nsp_layout_spec.json").read_text())

SAMPLE = {"afr": 13.2, "afr_target": 12.8, "oilt": 97, "fuelp": 43.5, "iat": 31, "volts": 14.1, "ign": 24.5}
TEXT = {"oilt_value": "97", "fuelp_value": "43.5", "iat_value": "31", "volts_value": "14.1", "ign_value": "24.5", "inj_value": "41"}
FRAC = {"oilt_bar": .47, "fuelp_bar": .54, "iat_bar": .31, "volts_bar": .76, "ign_bar": .58, "inj_bar": .41}


def needle_file(theme, pattern):
    stem = pattern.replace("*", theme)
    return next((P / f"classic/{theme}/needles").glob(stem.replace("_356px", "_up_356px").replace("_156px", "_up_156px")
                                                       .replace("_192px", "_up_192px").replace("_364px", "_up_364px") + "*"))


def classic(name, theme, lit=("lamp_log",)):
    sp = spec[f"classic_{name}"]
    bg = underlay(P / f"classic_{name}/{theme}/classic_{name}_background_{theme}.png", lit=lit)
    order = sorted(sp["gauges"].items(), key=lambda kv: 0 if kv[0] == "afr_target" else 1)
    for gid, s in order:
        v = SAMPLE[gid]
        a = s["start_angle_deg"] + (v - s["display_min"]) / (s["display_max"] - s["display_min"]) * s["sweep_deg"]
        n = Image.open(needle_file(theme, s["needle"])).rotate(-a, resample=Image.BICUBIC)
        bg.alpha_composite(n, (s["pivot_x"] - n.width // 2, s["pivot_y"] - n.height // 2))
    d = ImageDraw.Draw(bg)
    if "text" in sp:
        fnt = ImageFont.truetype(str(F / "BarlowCondensed-600.ttf"), 15)
        for key, val in (("afr_lcd", "13.2"), ("target_lcd", "12.8")):
            t = sp["text"][key]
            d.text((t["x"] + t["w"], t["y"] + t["h"] / 2), val, font=fnt, fill="#e9e04a" if theme == "day" else "#c9c03c", anchor="rm")
        wb = sp["text"]["tps_bar"]
        d.rounded_rectangle((wb["x"], wb["y"], wb["x"] + int(wb["w"] * .62), wb["y"] + wb["h"]), radius=2,
                            fill="#1d1b18" if theme == "day" else "#f08a54")
    for c in sp.get("plates_by_theme", {}).get(theme, []):
        if c["type"].startswith("Text"):
            fnt = ImageFont.truetype(str(F / "BarlowCondensed-600.ttf"), c["size"])
            d.text((c["x"] + c["w"], c["y"] + c["h"] / 2), TEXT[c["id"]], font=fnt, fill=c["color"], anchor="rm")
        else:
            d.rounded_rectangle((c["x"], c["y"], c["x"] + int(c["w"] * FRAC[c["id"]]), c["y"] + c["h"]), radius=2, fill=c["color"])
    return bg


DVALS = {"rpm_value": "3150", "speed_value": "47", "boost_value": "4.5", "boost_tgt_value": "12.0", "gear_value": "3",
         "afr_value": "13.2", "afr_tgt_value": "12.8", "ign_value": "24.5", "knock_value": "3", "knock_ret_value": "0.0",
         "inj_value": "41", "inj_pw_value": "6.80", "clt_value": "86", "oilp_value": "58", "oilt_value": "97",
         "fuelp_value": "43.5", "iat_value": "31", "tps_value": "62", "pedal_value": "64", "brake_value": "0",
         "batt_value": "14.1", "cl_trim_value": "-1.5", "fuel_value": "52", "trim_value": "2"}


def dense(theme):
    bg = underlay(P / f"diagnostic_dense/{theme}/diagnostic_dense_background_{theme}.png", lit=("pill_fan", "pill_pump", "pill_log"))
    d = ImageDraw.Draw(bg)
    for c in spec["diagnostic_dense"][theme]:
        if c["type"].startswith("Text") and c["id"] in DVALS:
            fnt = ImageFont.truetype(str(F / "Outfit-600.ttf"), c["size"])
            d.text((c["x"] + c["w"], c["y"] + c["h"] / 2), DVALS[c["id"]], font=fnt, fill=c["color"], anchor="rm")
        elif c["type"].startswith("Bar"):
            vid = c["id"].replace("_bar", "_value")
            if c["id"] == "rpm_bar":
                frac = 3150 / 8000
            else:
                try:
                    frac = (float(DVALS[vid]) - c["min"]) / (c["max"] - c["min"])
                except (KeyError, ValueError):
                    frac = 0
            d.rounded_rectangle((c["x"], c["y"], c["x"] + max(c["h"], int(c["w"] * frac)), c["y"] + c["h"]), radius=min(3, c["h"] // 2), fill=c["color"])
    return bg


if __name__ == "__main__":
    out = P / "previews"
    for name in ("tuning", "sixpack", "hybrid"):
        for th in ("day", "night"):
            classic(name, th).save(out / f"preview_classic_{name}_{th}.png")
    for th in ("dark", "light"):
        dense(th).save(out / f"preview_diagnostic_dense_{th}.png")
    print("ok")
