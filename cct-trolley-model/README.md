# CCT Trolley Model

A simulation of Central Cutting's Job Sequence and Panel Loading, run against 20
plan dates of real HaveCut data (1,863 tables, ~93 a day).

It answers one question: **how many trolleys does Central Cutting actually need,
and can three rule changes bring that under the 1,200 we own?**

---

## The finding, in one paragraph

Trolleys leave Central Cutting **53.6% full** — 2.7 of 5 compartments. At ~228
trolley loads a day and an estimated 7-day round trip, that means **1,593
trolleys have to be in circulation**, against a fleet of **1,200**. The factory
is roughly **393 trolleys short right now**, which is why WIP is chronically
unavailable. Three changes to how tasks are sequenced and how panels are loaded
take utilization to **71.3%** and the requirement to **1,169** — inside the
existing fleet, with no capex.

| | Utilization | Trolleys/day | Fleet needed @7d | vs 1,200 |
|---|---|---|---|---|
| **S0** Today | 53.6% | 228 | 1,593 | **393 short** |
| **S1** + same-MO sequencing | 59.4% | 200 | 1,402 | 202 short |
| **S2** + 2 batches per trolley | 65.4% | 182 | 1,274 | 74 short |
| **S3** + WIP hold (1 h, any WS) | **71.3%** | **167** | **1,169** | **31 spare** |

**Idle time does not move.** None of the three changes touches it. Idle time is the
spreader running out of table (rule G6): it costs 1,997 machine-minutes a day and
pushes a quarter of the spreading machines past the end of their shift. The cause is
that 24MC4 and 24MC5 each drive three spreading machines with one cutter at 95%
utilisation — and it takes both cutter routing and longer tables to fix, neither on
its own. Separate problem, separate business case, written up in **`IDLE_TIME.md`**.
Do not claim an idle-time saving for the three trolley changes.

---

## Running it

You need Python 3.9 or newer. Check with `python --version` (or `python3`).

```bash
pip install openpyxl
python run.py
```

That's it. ~10 seconds. It writes four files into `out/`:

| File | What it is |
|------|-----------|
| **`dashboard.html`** | **Open this.** Sliders for every assumption, numbers update live. |
| `results.xlsx` | Every scenario and every plan date, as a spreadsheet |
| `results.json` | The same numbers, machine-readable |
| `sweep.json` | What the dashboard's sliders read from |

### In Antigravity

Open the folder, then run `python run.py` in the terminal. To see the
dashboard, right-click `out/dashboard.html` → **Open Preview** (or open the file
in a browser). It is a single self-contained page — no server, no internet.

---

## Changing an assumption

Everything the model depends on is a named value in **`assumptions.py`**, with a
comment saying which rule it came from. Change a number, re-run `python run.py`,
and every output updates.

The three worth playing with first:

```python
CYCLE_DAYS_ESTIMATED = 7        # the round trip. AN ESTIMATE, NOT MEASURED.
WIP_HOLD_MINUTES = 60           # how long a part-filled trolley waits
MAX_BATCHES_PER_TROLLEY = 2     # the floor rule. never 3.
```

You don't have to edit files to explore — the dashboard has sliders for all of
these. Editing `assumptions.py` changes what counts as the *default*.

---

## What's in here

```
assumptions.py     every tunable value, with its rule reference
model.py           the simulation — read, sequence, time, load
scenarios.py       the four headline scenarios and the slider sweep
daytrace.py        per-day, per-table detail for the Simulation tab
run.py             runs everything, writes out/
dashboard.py       builds the HTML dashboard
idle_variants.py   regenerates the two tables in IDLE_TIME.md
data/planppc.xlsx  the HaveCut source data
SPEC_FOR_ISD.md    the three changes written as implementable logic
IDLE_TIME.md       why the machines stand idle, and what removes it
```

### The shifts

Everything in the model is minutes from **07:15**, the start of the day shift, so the
Gantt reads in real clock time.

| | Hours | Machines | Breaks | Working minutes |
|---|---|---|---|---|
| Day | 07:15–20:00 | all 13 spreaders, all 5 cutters | 11:45–12:45, 17:15–17:45 | 675 |
| Night | 18:00–05:00 | 24-01/02/03 and 24MC1 only | 22:00–22:30, 02:00–02:30 | 600 |

The two overlap 18:00–20:00, which adds no capacity — it is the same machine running
on. So a night-capable machine works **1,155 minutes**, a day-only machine **675**.
A task that meets a break pauses and resumes after it.

### The two tabs

`dashboard.html` has two views.

**Utilization** is the aggregate answer — sliders for every assumption, pooled over
all 20 plan dates. This is where the headline numbers come from.

**Simulation** is one plan date at a time, drawn twice:

1. **Job Sequence** as a Gantt. Thirteen `SPD` rows for the spreading machines, and
   under each cut group the `CUT` row for the machine that serves it. Each table gets
   a bar for its estimated spreading time and a second bar for its cutting time.
   Switch the sequencing rule from *Today* to *Same-MO* and the pairs appear as
   brackets — tables that were scattered across three machines land back-to-back on
   one. Hatching is blocking (rule G6). Bars are coloured by readiness, below.
2. **Panel Loading** — collapsed by default. The same day's panels going into
   compartments and trolleys, with a row per trolley showing how full it left and
   which tables it carries.

Between them sits the day's task list, and in the left rail the three changes plus the
cutting-end limit from `IDLE_TIME.md`.

The Simulation tab recomputes the loading stage in the browser so the controls respond
instantly. To stop that port drifting from `model.py`, the page checks its own
arithmetic against Python's for the same day and settings and says so on screen. If
that badge ever goes red, believe `run.py`.

### How the model works

Four stages, in `model.py`:

1. **Read** — each Plan Date in `HaveCut` becomes one day of tables. Type B
   only, `First Table = Y` excluded (rule J2). Kids and number-size markers stay
   in the timeline because they occupy machines, but carry no compartment maths
   (rule J3).
2. **Sequence** — the planner assigns tables to the 13 spreading machines in an
   order. Today it scatters a batch across the 3 machines of a cut group;
   change 1 pairs same-MO tables and keeps each pair on one machine.
3. **Time** — spreading and cutting run against the real shifts and breaks. Blocking
   (rule G6: the spreader waits for table to come free, and the lay in front gives its
   length back gradually as the cutter eats it) and cutting-machine contention fall
   out of this. See `IDLE_TIME.md`.
4. **Load** — cut panels go into compartments and trolleys. With WIP hold on, a
   part-filled trolley parks instead of leaving, and may be recalled.

**Stages 2 and 4 are deliberately separate, and that separation is the finding.**
The combine rule can only act on tables that are already back-to-back. Today's
sequencer rarely makes them back-to-back. That is why fixing the loading rule
alone was worth only +0.6 points in the July run — there was nothing for it to
act on.

---

## Task readiness statuses

The colour a task carries in the Auto Planning System when the day is sequenced.
These are the floor's own eight colours and their meanings; the Simulation tab
draws each table in the colour its condition earns.

| | Colour | Status | What it means | Where the model gets it |
|---|---|---|---|---|
| 1 | `#9bc2e6` pale blue | **Normal condition** | Fabric relaxed 24 h **and** pattern + cutting marker are in the planning module | everything below is satisfied |
| 2 | `#833c0c` brown | **Normal · cut queue** | A normal task that was queued **by hand**, not by the system | **not simulated** — manual intervention is outside the model |
| 3 | `#ffd966` amber | **Normal · stretch spreading** | The last task on a fabric batch, spreading the last few hundred yards. Always at the end of a batch, never in between | the batch's final table by `Pull Date` |
| 4 | `#a9d08e` green | **No pattern, enough fabric** | Fabric relaxed, but no pattern in the planning module | `Marker Date` is empty |
| 5 | `#f4b084` orange | **Have pattern, not enough fabric** | Pattern is in, but the fabric has not relaxed long enough | the relax simulation, below |
| 6 | `#7030a0` purple | **No pattern, not enough fabric** | Neither condition met. The planner normally holds these back until they qualify | both of the above |
| 7 | `#305496` navy | **No fabric** | No fabric information in the system at all. Should not happen | **never fires** — `Lot` and `Batch No` are filled on all 2,717 rows |
| 8 | `#d9d9d9` grey | **Completed** | Spreading and cutting finished | `Pull Date` is at or before the tab's time cursor |

Priority runs bottom-up: finished work is grey whatever else was true of it, and
**stretch spreading only qualifies a task that is otherwise normal**.

### Where each one actually comes from

- **Pattern** — the marker ratio (`S/3,M/2,L/3`), which is filled in at latest 1.5 h
  after the plan is uploaded, so in practice it is never the constraint. Every one of
  the 1,863 modelled tables has one — the 852 rows with no `Marker Date` are all Type
  C or first-table rows that rule J2 already excludes — so statuses 4 and 6 do not
  fire here. Kept in the legend because the planning system still shows them.
- **Completed** — `Pull Date`, which is the **actual finished-spreading timestamp**,
  not a plan. Drag the time cursor and tables grey out in the order they really
  finished. It sits *after* the Plan Date on 98.7% of rows.
- **Stretch spreading** — the last table of each `Batch No`, ordered by `Pull Date`.
- **Fabric relaxing** — **a proxy, not a measurement.** See below.

### Relaxing is a precondition, not a variable

Fabric must relax **24 hours** before it may be spread. A table is not released to the
floor until that is satisfied, so the simulation treats every planned table as
relaxed and statuses 5 and 6 read zero. They stay in the legend because the planning
system still shows them.

**Stretch spreading covers 823 of 1,863 tables (44%)** — batches average 2.26 tables,
so being the last table of a batch is common rather than exceptional.

---

## What to distrust

Read this before quoting any number from here.

- **The 7-day round trip is an estimate, not a measurement.** It is the single
  number the whole business case turns on, and nobody has timed it. At the
  5-day allowance today needs 1,138 trolleys and *does* fit. Measuring the real
  cycle for one week is the cheapest and highest-value thing on this list.
- **Nobody has costed how a parked trolley reaches a different workstation.**
  Change 3 assumes it can. If it can't, change 3 is worth +0.5 points instead of
  +5.9. See §4 of `SPEC_FOR_ISD.md`.
- **Half the tables do not finish spreading on the day they were planned for.**
  `Pull Date` is the actual finished-spreading timestamp. Across the 1,863 tables in
  the export, **49% finish after their plan date and 14% more than a day late** — but
  the median table finishes about **23 minutes before midnight** on its plan date, so
  the typical table is not late at all. The lateness is in the tail: of the **912
  tables that do run late, half slip more than half a day**, and the mean slip among
  them is 0.90 days. That is counted from the data, not inferred. Every day the model
  runs is a *planned* day; the sequence it produces is what the plan asks for, not what
  the floor did. The Simulation tab's time cursor runs for **up to three days** from
  07:15 on the plan date, which covers most of that tail but not all of it — on 12 of
  the 20 dates some work still finishes past the end of the slider, and 2026-05-18's
  latest actual finish is **8.3 days** out. The cap is a deliberate trade: a slider
  long enough for the worst date would be too coarse to be useful on any of them.
- **Fabric arrival is not in the data at all.** The model assumes the 24-hour
  relaxing rule is met, because a table is not released until it is. It cannot tell
  you how often that assumption fails in practice.
- **Breaks are assumed to stop the machines.** If relief staffing keeps them running,
  `BREAKS_STOP_MACHINES = False` is worth about 150 minutes a machine a day.
- **Component is not in the data.** The model treats each table as one component
  set. The real system must still enforce same-component.
- **Film size uses the H5 mapping, not real Net_Rate.** Real Net_Rate puts more
  sizes on one film, which would make these numbers *better*, not worse. So
  the results here are conservative on that axis.
- **C-table spreading time is estimated at 10 minutes** (rule N).
- **Shrinkage and shade-lot data are missing**, so batch merging *at spreading*
  is untested. This model only merges batches at *loading*.
- **Modelled volume is ~68,700 pieces/day on trolleys**, below the ~90,000 total,
  because non-universal markers are excluded from compartment maths.
  Utilization is a ratio and holds regardless; the absolute trolleys-per-day
  figures are therefore conservative.

---

## Sensitivity: what is *not* the constraint

Two obvious suspects were tested and neither is binding:

| Constraint | As written | Relaxed to | Gain |
|---|---|---|---|
| Trolleys per combine | ≤4 (H8) → 65.4% | no cap → 66.1% | +0.7 |
| Tables per trolley set † | pairs → 65.3% | any chain → 65.8% | +0.5 |
| Both together † | 65.3% | 68.4% | +3.1 |

† **These two rows come from an earlier variant of the model that no longer exists
in this repo, and cannot be regenerated from it.** `_loading_events` pairs on
`seq[i], seq[i+1]`, so a chain of arbitrary length would need a new `Scenario`
field and a loop to measure. Their 65.3% baseline is the pre-correction figure —
today's S2 is 65.4%. Read them as direction, not as current numbers. The
trolleys-per-combine row was regenerated today: `MAX_TROLLEYS_PER_COMBINE` is a
plain constant in `assumptions.py`, so removing the cap is a one-line change.

The binding constraint is **adjacency** — two tables can only share a trolley if
they are spread back-to-back at one workstation. That is why change 1 (which
creates adjacency) and change 3 (which removes the need for it) are worth far
more than raising any cap.

---

## Reproducing the deck

Every number in `CCT_Trolley_Solution.pptx` and in the published report comes
from `out/results.json`. If a figure in a slide and a figure here disagree, this
repo is right — it is the thing that was actually run.
