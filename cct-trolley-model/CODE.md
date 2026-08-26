# CODE.md — what this project has settled

Kept by the **compacter** agent. Read it before changing anything; it holds decisions,
measured numbers, options already ruled out, and the traps that have bitten.

If this file and the code disagree, **the code wins** and this file is out of date.

Last updated: **2026-08-26**

---

## The two problems

| | Question | Where |
|---|---|---|
| **Trolleys** | Do three rule changes bring the fleet requirement under 1,200? | `README.md`, `SPEC_FOR_ISD.md` |
| **Idle time** | Why do spreading machines stand idle, and what fixes it? | `IDLE_TIME.md` |

**They are independent.** Every idle-time variant tested leaves trolley utilization at
54.4% and 225 trolleys/day. Never claim an idle-time saving for the three trolley
changes, or vice versa.

---

## Measured vs assumed

The distinction the whole project turns on.

| Value | Status | Note |
|---|---|---|
| `SPREADING_TABLE_LENGTH_M = 21.2` | **measured** | user, 2026-08-26 |
| Shift hours and breaks | **measured** | user, 2026-08-26 |
| `Marker Date`, `Pull Date`, marker ratios, layers | **measured** | from `HaveCut` |
| `CYCLE_DAYS_ESTIMATED = 7` | **estimate** | never timed; the trolley case turns on it |
| `C_TABLE_EXTRA_MINUTES = 10` | **estimate** | rule N |
| `MACHINE_FILL_TARGET = 0.70` | planning heuristic | not a written rule |
| Component, real Net_Rate | **absent** | see "Not in the data" |

---

## Settled decisions

- **Shifts.** Day 07:15–20:00, all 13 spreaders and 5 cutters. Night 18:00–05:00, only
  24-01/02/03 and 24MC1. Breaks 11:45–12:45 and 17:15–17:45 by day, 22:00–22:30 and
  02:00–02:30 at night; machines stop for them (`BREAKS_STOP_MACHINES`). The 18:00–20:00
  overlap adds no capacity — same machine running on. Net: **675 min** day-only,
  **1,155 min** night-capable. All times are minutes from 07:15, so the Gantt reads in
  real clock time.
- **Fabric relaxing is a precondition, not a variable.** 24 h before spreading, and a
  table is not released until it is met — so every planned table is treated as relaxed
  and statuses 5 and 6 read zero. An earlier "fabric issued ahead" slider was removed.
- **Pattern is never the constraint.** It is the marker ratio, filled within 1.5 h of
  the plan upload. All 1,863 modelled tables have one.
- **Net_Rate is universal — use the H5 mapping.** A scheme switcher was built and then
  removed at the user's instruction.
- **Blocking is a length problem, not a slot count.** A lay occupies its marker length;
  cutting consumes that length *progressively* as the lay is fed to the cutter, so
  space returns gradually. Modelling it as two slots emptying at `cut_end` overstated
  blocking by **68%** (3,244 vs 1,930 min/day).
- **Idle time excludes breaks and shift ends.** A machine that is unstaffed is not
  starved; that time never enters the blocked percentage.

---

## Current numbers

Headline, after the shift-model correction (the correction barely moved them, which is
the good news — the business case survived):

| | Utilization | Trolleys/day | Fleet @7d |
|---|---|---|---|
| S0 Today | 54.4% | 225 | 1,575 |
| S1 + same-MO sequencing | 59.4% | 200 | 1,402 |
| S2 + 2 batches per trolley | 65.4% | 182 | 1,274 |
| S3 + WIP hold | 71.3% | 167 | 1,169 — **fits in 1,200** |

Idle time at the real 21.2 m table: **1,930 blocked min/day**, 25% of machine-days
overrun their shift, last cut finishes 00:45.

Data: **20 plan dates, 1,863 tables.** If either moves, something upstream changed.

---

## Ruled out, with the numbers that killed it

Do not re-propose these without new information.

| Idea | Result |
|---|---|
| Cutter flexibility alone | blocking 1,930 → 1,601. Helps, but cannot create capacity |
| Tuning `MACHINE_FILL_TARGET` | 0.60 and 0.85 both worse than 0.70 |
| Balancing cut groups by capacity not spreader count | fewer overruns but a longer day |
| Raising the ≤4 trolleys-per-combine cap (H8) | +0.8 points |
| Chaining more than two tables per trolley set | +0.5 points |
| Change 2 without change 1 | +0.6 points — the combine rule needs adjacency to act on |

**The binding constraint on trolleys is adjacency.** On idle time it is the
spreader-to-cutter ratio: cutting is 47% of spreading time, so one cutter sustains
~2.1 spreaders; 24MC4 and 24MC5 run three each at 93% cutter utilisation.

---

## Not in the data

Checked directly — do not plan around these.

- **No `Net_Rate` column.** All 66 `HaveCut` headers and 13,136 shared strings searched.
  Columns AY–BE (100–160) are kids number-sizes.
- **No fabric arrival or relax-start time.**
- **`Cut Date` is empty** (1 row of 2,717).
- **No component.** Each table is treated as one component set.
- **`Marker Date` missing on 852 rows — all excluded by rule J2 anyway.**
- `Pull Date` is the **actual finished-spreading timestamp**, not a plan.

---

## Traps

Each of these was silently wrong until a gate caught it.

1. **Never sort `pieces_by_size`.** `compartments_for` walks it in insertion order, and
   that decides which film width opens a trolley first — which changes the answer once
   the 52 bays are full.
2. **Never round `cut_end` in the trace.** The page sorts loading events by it and
   times the WIP hold against it; rounding reorders near-simultaneous tables.
3. **Python `round()` breaks ties to even, JS `toFixed()` rounds up.** 4,345 trolleys
   over 20 days is exactly 217.25.
4. **`max_batches` 2 and 3 are identical** — `load_trolleys` gates the parked-trolley
   top-up on the global `A.MAX_BATCHES_PER_TROLLEY`, not `scenario.max_batches`.
5. **Grid items default to `min-width: auto`**, so wide content stretches its column and
   scrolls the whole page. Use `minmax(0, 1fr)` and `min-width: 0`.

---

## Building

```bash
python run.py          # the real build — rewrites everything in out/
```

**Python is not installed on this machine.** A Node port in the session scratchpad
(`model.js`, `build.js`, `validate.js`, `xlsx.js` — no dependencies, reads the xlsx via
`zlib`) can build the page instead. It was pinned against the real Python output first:
78 sweep combinations × 8 fields, all exact.

**What the port may and may not do.** It may build the page. It is *not* a second
source of truth — `out/results.json` currently carries a `generated_by` field saying so,
and `python run.py` should be run to confirm the numbers when Python is available.
Never hand-write `out/dashboard.html`.

### Gates that must pass before publishing
- **Parity: 4,680/4,680** — the page's own loading maths against the model, every day,
  table length and setting.
- 23 loading-port tests, 22 status/shift/clock tests.
- Layout assertions, tags balanced, no external URLs.

---

## Open questions

1. **The 7-day trolley cycle has never been measured.** The single number the business
   case turns on. At the 5-day allowance today already fits. Measuring it for one week
   is the cheapest, highest-value thing on the list.
2. **How does a parked trolley physically reach a different workstation?** Worth
   +6.4 points if it can, +0.7 if it cannot. Production must answer, not ISD.
3. **Can the planning system show batch at compartment level?** If not, change 2 cannot
   ship.
4. **Is there floor space to extend the spreading tables** beyond 21.2 m?
5. **Cutting-machine travel time is not modelled**, so real blocking is likely worse
   than 1,930 min/day, not better.
