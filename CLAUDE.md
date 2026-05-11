# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **data/documentation repository**, not a codebase. It contains base ECU tuning maps and wiring documentation for a turbocharged Classic Mini build, published as a public reference for other Classic Mini enthusiasts. There is no build system, test suite, or runtime — the only "build" step is WireViz diagram generation (see below).

The maps here are the public mirror of what's sold at https://store.classicminidiy.com/collections/efi-base-maps. The README's disclaimer ("**NOT PLUG AND PLAY**", requires dyno tuning) is load-bearing — never characterize a map as ready to flash to a vehicle, and preserve the disclaimer wording on any user-facing edits.

## What you can and can't edit here

**Most files in this repo are binary proprietary tuning-software formats.** You cannot read, diff, or edit them with normal tools — they round-trip only through their vendor software:

| Extension                                            | Software (open in this to edit)                                       |
|------------------------------------------------------|-----------------------------------------------------------------------|
| `.nexmap` (`.nexR3-*`, `.e1500-*`, `.e1000-*`)       | Haltech NSP / ESP — Nexus R3, Elite 1500, Elite 1000                  |
| `.nexmap` (`.e550-*`, `.e750-*`) and `.htc`          | Haltech ECU Manager / NSP — Elite 550 / 750                           |
| `.msq`                                               | TunerStudio (Speeduino / MegaSquirt) — XML, technically text but don't hand-edit |
| `.map`                                               | Emerald EMU / DTAFast configurator                                    |
| `.emupro`                                            | ECUMaster EMU Pro                                                     |
| `.MaxxECU-save`                                      | MaxxECU                                                               |
| `.mjlj`                                              | MegaJolt Lite Jr.                                                     |
| `.cal`                                               | Haltech sensor calibration table (text-ish but vendor-specific)       |
| `.hlgzip`                                            | Haltech compressed PC log archive                                     |
| `.xlsx`                                              | Excel — the `D400 to Haltech.xlsx` pin-mapping spreadsheet            |

The **only files Claude should hand-edit** are:
- `*.yml` under `diagrams/` (WireViz sources — see workflow below)
- `README.md`, `CLAUDE.md`, and other markdown
- `.gitignore`, `.gitattributes`, `.github/FUNDING.yml`

If asked to "update a map," clarify whether the user wants the binary file replaced (they exported a new version from their tuning software) or whether they want help with the surrounding docs/diagrams.

## Repository layout, beyond what's obvious from `ls`

The top-level platform directories follow `README.md`. A few sub-organizational patterns are not self-explanatory:

- **All directories are kebab-case.** Haltech product names (`R3`, `E550`, `E750`, `E1500`, `E1000`) keep their proper-noun casing — everything else is lowercase.
- **`haltech/R3/`** is the actively maintained platform. Subfolders:
  - `5-port/` — standard A-series 5-port head (the default Mini config)
  - `16v/` — 16-valve conversion variant (tracked separately because the entire VE/ignition table differs)
  - `dyno-reference-maps/` — versions validated on a dyno; kept as known-good baselines (subfolder `haltech-ky/` for end-of-day Haltech KY dyno session output)
  - `all-logs/` — `.csv` + `.hlgzip` PC log captures, organized as `<year>/<YYYY-MM-DD-description>/`. Date is the **file export date** when no session date is recorded; folders may include both (e.g. `2024-04-16-dyno-march-15`)
  - `reference-maps/` — collaborator drafts (`elliot/`, `james-edits/`)
- **`haltech/E1500/`, `haltech/E1000/`** hold collaborator reference maps for the older Elite platforms (Steve, Elliot). No first-party Cole map exists for these — they're sources of ideas, not active baselines.
- **Reference maps are organized platform-first, then collaborator** (e.g. `haltech/R3/reference-maps/elliot/`, `haltech/E1500/reference-maps/steve/`). Don't relocate them back to a flat collaborator-only structure — the platform routing is intentional.
- **`haltech/wiring-diagrams/`** is distinct from the top-level `diagrams/` directory. It holds Haltech-specific reference material (PDF/JPEG diagrams, the `D400 to Haltech.xlsx` pin-map spreadsheet, the ECU pinout `IOReport.pdf`) — *not* WireViz sources.
- **`diagrams/`** is the only WireViz workflow in the repo (see next section).
- **16V variants** exist across platforms with very different completion levels — see the support matrix in `README.md` before assuming a 16V map exists for a given ECU.

## Git LFS

Logs under `haltech/R3/all-logs/` are tracked via Git LFS. The patterns live in `.gitattributes`:
```
haltech/R3/all-logs/**/*.csv     filter=lfs diff=lfs merge=lfs -text
haltech/R3/all-logs/**/*.hlgzip  filter=lfs diff=lfs merge=lfs -text
haltech/R3/all-logs/**/*.zip     filter=lfs diff=lfs merge=lfs -text
```

When adding a new log file, just `git add` it — the LFS filter is automatic. The LFS migration kept old blob versions in history (no force-push); to actually shrink the repo you'd run `git lfs migrate import --include="*.csv,*.hlgzip,*.zip" --everything` and force-push, which Cole has not authorized as a default.

GitHub free LFS quota is 1 GB storage + 1 GB bandwidth/month. Current logs are ~692 MB — flag to Cole if you're about to add another large batch.

## WireViz workflow (the only "build" in this repo)

Wiring diagrams under `diagrams/<component>/` are generated from a single `<component>.yml` source via [WireViz](https://github.com/wireviz/WireViz). All generated outputs (`.svg`, `.png`, `.html`, `.bom.tsv`, `cross-section.png`) are committed alongside the source.

To regenerate after editing a YAML:

```bash
# from the component's directory, e.g. diagrams/dbw-pedal/
wireviz dbw-pedal.yml
```

This overwrites the `.svg`, `.png`, `.html`, and `.bom.tsv` siblings. **Always commit the regenerated outputs together with the YAML change** — consumers of this repo (including the classicminidiy.com knowledgebase) link to the rendered files directly, not the source. WireViz is Cole's own fork at `~/Development/WireViz/`; install it from there if not on `PATH`.

YAML schema reference: each diagram defines `connectors`, `cables`, and `connections`. See `diagrams/dbw-pedal/dbw-pedal.yml` for the canonical shape (pinlabels, pins, colors, plus optional `image:` blocks for cross-sections). Wire color codes use WireViz's two-letter shorthand (`BKWH` = black/white, `WHBN` = white/brown, etc.) — preserve these even when they look like typos.

## Conventions specific to this repo

- **Don't sanitize Mini terminology.** "5-port", "16V", "drive-by-wire", "trigger sensor", "TPS", "DBW", "VE table", "AFR" are correct domain language — not jargon to expand.
- **Don't update the platform support matrix in `README.md` speculatively.** Flipping `started` → ✅ is a real claim that the map exists, has been opened in the vendor tool, and produces sensible output. Only change a status when the user confirms.
- **Binary file changes are opaque in diffs.** When a user replaces a `.nexmap` / `.htc` / `.msq` / `.map`, the commit message must describe what changed (e.g. "update R3 5-port map: revised VE table 2000-3500 RPM, leaner cruise") — Git can only show "binary file changed."
- **No CI, no hooks, no test runner.** This repo's only check is `git status`. Don't suggest adding lint or test infrastructure unless asked — the artifacts are tuning files, not code.

## Cross-property context

This repo feeds the **Classic Mini DIY** ecosystem (see `~/Development/CLAUDE.md`). The maps here are referenced by:
- The store at `store.classicminidiy.com` (paid downloads)
- The knowledgebase site `classicminidiy/` (Nuxt 4) which links to wiring diagrams in `diagrams/`

Changes to the WireViz outputs may need a corresponding asset refresh on the knowledgebase site, but that's tracked there — not here.
