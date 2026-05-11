# James Edits

Drafts from James iterating on fuel, post-start, and closed-loop O2 behaviour for the BadWolfTurbo R3 map.

These are working files — none has been validated as the canonical baseline. The Haltech NSP version embedded in the filename (`-1-24-5`, `-1-25-4`, `-1-25-5`) is the closest thing to a chronological marker.

## Files (oldest NSP version → newest)

| File | NSP version | What it changed |
|---|---|---|
| `disabled-zero-demand-fuel-upped-post-start-coolant-temp.nexR3-1-24-5.nexmap` | 1.24.5 | Disabled zero-demand fuel; raised post-start fuel and coolant-temp fuel |
| `some-nudges.nexR3-1-24-5.nexmap` | 1.24.5 | Small adjustments (description was "some nudges" with no detail) |
| `cole-james-edit-1.nexR3-1-25-4.nexmap` | 1.25.4 | James's first pass over Cole's working map |
| `mega-fuel-changes.nexR3-1-25-4.nexmap` | 1.25.4 | Large fuel-table revisions |
| `james-edit-2-missing-cole-changes-between.nexR3-1-25-4.nexmap` | 1.25.4 | James's second pass; does not include Cole's intermediate edits |
| `fuel-changes-o2-only-adds-fuel.nexR3-1-25-5.nexmap` | 1.25.5 | Restricted closed-loop O2 to only add fuel (no leaning) |

Order within the same NSP version is approximate — confirm against Haltech file metadata before merging any of these forward.
