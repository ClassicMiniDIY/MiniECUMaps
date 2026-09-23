# maps.json — machine-readable catalog of this repo

**Date:** 2026-09-22
**Status:** Merged 2026-09-22 — ClassicMiniDIY/MiniECUMaps#1 and ClassicMiniDIY/classicminidiy#896 (payload trim in #897)

## Problem

The platform support matrix exists in two hand-edited copies:

1. `README.md` in this repo.
2. A hardcoded `items` array in `classicminidiy/app/pages/maps.vue`.

The two copies drifted. Example: Emerald 16V is `WIP` in the README and `Included` on the site. ECUMaster and MaxxECU VE / boost / idle are `---` in the README and `WIP` on the site.

The repo is also opaque to tools and LLMs. The map files are binary vendor formats. The only metadata is the filename. An agent cannot tell which file is the current base map, which is a collaborator draft, or which software version opens it.

## Decision

Add `maps.json` at the repo root. It is the single source of truth for:

- The platform × feature support matrix.
- The list of map files, with role, ECU, engine, software, and software version.
- The list of WireViz diagrams and their rendered outputs.

The site reads `maps.json` from `raw.githubusercontent.com` through a cached server route. The site no longer hardcodes the matrix.

The README matrix stays hand-written for GitHub readers. `CLAUDE.md` makes it a rule that both change in the same commit.

## Schema (version 1)

```jsonc
{
  "schemaVersion": 1,
  "updated": "YYYY-MM-DD",            // bump on every edit
  "repository": "https://github.com/ClassicMiniDIY/MiniECUMaps",
  "store": "https://store.classicminidiy.com/collections/efi-base-maps",
  "disclaimer": "…",                  // same wording as README; NOT PLUG AND PLAY
  "statuses": { "<status>": "<meaning>" },
  "features": [{ "id": "ignitionMap", "label": "Ignition Map" }],
  "platforms": [{
    "id": "haltech", "name": "Haltech", "directory": "haltech/",
    "software": "Haltech NSP / ESP",
    "features": { "ignitionMap": "included", … }   // one key per features[].id
  }],
  "files": [{
    "path": "haltech/R3/5-port/BadWolfTurbopm.nexR3-1-30-0.nexmap",
    "platform": "haltech",            // platforms[].id
    "ecu": "Nexus R3",
    "engine": "5-port" | "16v" | null,
    "role": "base" | "working" | "dyno-reference" | "collaborator-reference" | "dash",
    "software": "Haltech NSP",
    "softwareVersion": "1.30.0" | null,
    "contributor": "cole" | "elliot" | "james" | "steve" | "haltech-ky"
  }],
  "diagrams": [{
    "id": "dbw-pedal", "title": "…", "source": "diagrams/dbw-pedal/dbw-pedal.yml",
    "svg": "…", "png": "…", "bom": "…"
  }]
}
```

### Status values

| Value          | README  | Meaning                                          |
|----------------|---------|--------------------------------------------------|
| `included`     | ✅      | In the map and working                           |
| `started`      | started | Base file checked in, not validated              |
| `wip`          | WIP     | Actively in progress                             |
| `not-included` | ❌ / --- | ECU supports it; the map does not include it yet |
| `na`           | N/A     | The ECU cannot do this                           |

`schemaVersion` is bumped only on a breaking shape change. The site route rejects an unknown `schemaVersion` and shows its error state.

## Site consumption

- `classicminidiy/server/api/github/maps-manifest.ts` fetches `https://raw.githubusercontent.com/ClassicMiniDIY/MiniECUMaps/main/maps.json`, caches the last valid copy per Worker instance for 30 minutes (serving it stale if a refresh fails), and returns `features` + `platforms` + `updated`.
- `app/pages/maps.vue` builds the table from the response. Feature labels come from the page i18n keys by `features[].id`. The manifest `label` is the fallback.

## Rollout order

1. Merge the repo PR first, so `maps.json` exists on `main`.
2. Then merge the site PR. Before step 1 the site route returns 502 and the table shows the error state.

## Not done (deliberately)

- No CI or schema validator. The repo has no CI by design. Validate path existence by hand after edits:
  `python3 -c "import json,os;[print('MISSING',f['path']) for f in json.load(open('maps.json'))['files'] if not os.path.exists(f['path'])]"`
- No README generation from the manifest. That would add a build step to a data repo.
