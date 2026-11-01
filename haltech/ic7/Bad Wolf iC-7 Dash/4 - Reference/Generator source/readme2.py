"""Append the round-2 screens to README.md from the spec."""
import json, re
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "out" / "Haltech-iC7-CMDIY"
s = json.loads((P / "nsp_layout_spec.json").read_text())
md = (P / "README.md").read_text()
md = md.split("\n## Round 2")[0].rstrip() + "\n"


def gauge_rows(sp):
    rows = []
    for k, v in sp["gauges"].items():
        b = v["needle_box"]
        rows.append(f"| {k} | {v['channel']} | {v['display_min']} → {v['display_max']} {v['units']} | ({v['pivot_x']}, {v['pivot_y']}) | x {b['x']}, y {b['y']}, {b['w']}×{b['h']} | `{v['needle']}` |")
    return "\n".join(rows)


HDR = "| Gauge | Channel | Range | Pivot | Needle box | Needle |\n|---|---|---|---|---|---|\n"
out = ["\n## Round 2", "",
       "### Splash options", "",
       "- `splash/splash_bad_wolf_plate.png`: chrome-rimmed black plate on the crinkle ground.",
       "- `splash/splash_bad_wolf_dial.png`: a magnolia gauge face carrying the name.",
       "- `splash/splash_bad_wolf_car.png`: the Bad Wolf illustration with the name set large.",
       "- `splash/splash_cmdiy_logo.png`: the first version, kept for reference.", "",
       "### Classic · Tuning (`classic_tuning/`)", "",
       "Same layout as the classic screen, filled with what the physical gauges don't show. The centre is a big AFR gauge with a lambda inner ring, an orange stoich mark at 14.7, and an orange target needle (`needle_target_large`) under the black needle. The LCD shows AFR and target. The bottom window is wastegate duty. Lamps: KNOCK (amber) and LOG (green).", "",
       HDR + gauge_rows(s["classic_tuning"]), ""]
t = s["classic_tuning"]["text"]
out += ["| Item | Box | Channel |", "|---|---|---|"]
for k, v in t.items():
    out.append(f"| {k} | x {v['x']}, y {v['y']}, {v['w']}×{v['h']} | {v['channel']} |")
for k, v in s["classic_tuning"]["lamps"].items():
    out.append(f"| {k} | place x {v['place_x']}, y {v['place_y']} (`{v['image']}`) | {v['channel']} |")
out += ["", "### Classic · Six-pack (`classic_sixpack/`)", "",
        "Six equal 220 px gauges: AFR, oil temp, fuel pressure, intake air, volts and ignition timing. Uses the new `needle_medium` (192 px).", "",
        HDR + gauge_rows(s["classic_sixpack"]), "",
        "### Classic · Hybrid (`classic_hybrid/`)", "",
        "The big AFR gauge on the left and six magnolia data plates on the right. The plates take an NSP text value (Barlow Condensed 54 px) and a thin bar.", "",
        HDR + gauge_rows(s["classic_hybrid"]), "",
        "| Plate component | x, y | w×h | Channel | Range | Day colour | Night colour |", "|---|---|---|---|---|---|---|"]
pd, pn = s["classic_hybrid"]["plates_by_theme"]["day"], s["classic_hybrid"]["plates_by_theme"]["night"]
for a, b in zip(pd, pn):
    rng = f"{a.get('min', '')} → {a.get('max', '')}" if "min" in a else ""
    out.append(f"| {a['id']} | {a['x']}, {a['y']} | {a['w']}×{a['h']} | {a['channel']} | {rng} | {a['color']} | {b['color']} |")
for k, v in s["classic_hybrid"]["text"].items():
    out.append(f"| {k} | {v['x']}, {v['y']} | {v['w']}×{v['h']} | {v['channel']} | | | |")
out += ["", "### Diagnostic · Dense (`diagnostic_dense/`)", "",
        "Twenty tiles in four themed rows (boost and fuelling; spark and injection; temperatures and pressures; driver inputs and electrics), a compact RPM row, and the same status pills. Values are Outfit SemiBold 32 px. The pill images are the ones in `diagnostic/{theme}/`.", "",
        "| Component | Type | x, y | w×h | Channel | Range |", "|---|---|---|---|---|---|"]
for c in s["diagnostic_dense"]["dark"]:
    rng = f"{c.get('display_min', c.get('min', ''))} → {c.get('display_max', c.get('max', ''))}" if ("min" in c or "display_min" in c) else ""
    out.append(f"| {c['id']} | {c['type']} | {c['x']}, {c['y']} | {c['w']}×{c['h']} | {c['channel']} | {rng} |")
out += ["", "Brake pressure (SPI3) is shown in psi with a 0–1500 range; set it to your sensor. CL TRIM is Haltech's closed-loop fuel correction; if your firmware names it differently, pick the nearest channel.", ""]
(P / "README.md").write_text(md + "\n".join(out))
print("ok")
