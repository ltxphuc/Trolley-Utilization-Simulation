# Job Sequence & Panel Loading — change spec

**For:** ISD, to implement in the Auto Planning System
**Scope:** Central Cutting only — Job Sequence, Cutting & Panel Loading
**Status:** simulated on 20 plan dates of real HaveCut data; not yet piloted

This document says what to build. The reasoning and the numbers are in
`README.md` and `out/dashboard.html`.

---

## 0. Summary

Three changes, in the order they should be built. Each one is worth something on
its own, and each depends on the one before it.

| # | Change | Where | Utilization |
|---|--------|-------|-------------|
| — | Today | — | 53.6% |
| 1 | Job Sequence places same-MO tables back-to-back | Job Sequence | 59.4% |
| 2 | A trolley may carry 2 fabric batches | Panel Loading combine rule | 65.4% |
| 3 | A part-filled trolley waits in CCT WIP and is recalled | Panel Loading + WIP | 71.3% |

**Change 2 without change 1 is worth almost nothing** (+0.6 pt in the July run).
The combine rule can only act on tables that are already adjacent, and today's
Job Sequence rarely makes them adjacent. Do not ship 2 without 1.

---

## 1. The rules as they are today

From `Job Sequence / Panel Loading Suggest Logic`, current logic.

### 1a. Combine requirements (trolleys of task X wait for task A)

| # | Condition | Change |
|---|-----------|--------|
| 1 | Continuously spread at 1 WS | **KEEP** — physical, the trolley must still be standing there |
| 2 | Same MO | KEEP |
| 3 | **Same batch** | **RELAX** → change 2 |
| 4 | Same component | KEEP |
| 5 | Same film code | KEEP |
| 6 | Trolleys still have empty compartments | KEEP |
| 7 | Current task needs ≤ 4 trolleys | KEEP (rule H8) |
| 8 | Trolleys still have empty compartments | KEEP (duplicate of 6) |
| 9 | **Trolley may wait only if tasks are spread and cut continuously at 1 WS without the cutting MC changing WS** | **REMOVE** → change 3 |

### 1b. Come-back requirements (trolleys return from CCT WIP)

| # | Condition | Change |
|---|-----------|--------|
| 1 | Same MO | KEEP |
| 2 | **Same batch** | **RELAX** → change 2 |
| 3 | Same colour | KEEP |
| 4 | Same component | KEEP |
| 5 | Same film code | KEEP |
| 6 | Trolleys still have empty compartments | KEEP |

---

## 2. CHANGE 1 — Job Sequence: same-MO adjacency

### What happens today

Job Sequence clusters by MO + colour + batch, then distributes that cluster
across the 3 spreading machines of one cut group (flowchart 3.3a). Two tables
that *could* share a trolley end up on different machines, so combine condition
1 is almost never satisfied.

### What to build

Cluster by **MO + colour** (drop batch from the cluster key). Inside each
cluster, pair tables up *before* assigning them to a machine, and assign each
pair to **one** machine as **consecutive** entries in that machine's queue.

```
FOR each cluster of tables sharing (MO, colour):
    sort tables by (batch, descending spread_time)
    units = []
    taken = {}

    # PASS 1 — pair same-batch tables first  (stated priority)
    FOR i IN tables:
        IF taken[i]: CONTINUE
        FOR j IN tables AFTER i:
            IF taken[j]: CONTINUE
            IF batch[i] != batch[j]: CONTINUE
            IF NOT can_combine(i, j): CONTINUE
            units.APPEND([i, j]); taken[i] = taken[j] = TRUE; BREAK

    # PASS 2 — then pair different batches of the same MO
    FOR i IN tables:
        IF taken[i]: CONTINUE
        FOR j IN tables AFTER i:
            IF taken[j]: CONTINUE
            IF batch[i] == batch[j]: CONTINUE
            IF NOT can_combine(i, j): CONTINUE
            units.APPEND([i, j]); taken[i] = taken[j] = TRUE; BREAK

    units += [[t] for each unassigned table]

    # assign whole units, never splitting a pair across machines
    FOR unit IN units SORTED BY total spread_time DESC:
        machine = least_loaded_machine_with_room(cut_group, unit.spread_time)
        machine.queue.EXTEND(unit)        # <-- consecutive. this is the point.
```

**The one thing that must not be lost:** `machine.queue.EXTEND(unit)` appends both
tables of a pair adjacently to the same machine. If a later load-balancing pass
splits pairs across machines, change 1 is undone and changes 2 and 3 lose most
of their value.

### Guard rails

- Machine capacity: a machine's queued spreading minutes should not exceed
  ~70% of its staffed window; the remainder absorbs blocking (rule G6).
  If a pair does not fit, place it on another machine in the same cut group —
  do not split it.
- Batch relaxing (24h per batch) still gates whether a table is releasable at
  all. Change 1 reorders releasable tables; it does not release them early.

---

## 3. CHANGE 2 — Panel Loading: two batches per trolley

### What to build

Drop **combine condition 3** and **come-back condition 2** ("same batch").
Add one new constraint in their place:

```
MAX_BATCHES_PER_TROLLEY = 2      # hard limit. never 3.
```

Compartment rules do not change:

- a compartment still holds **one batch only** (rule H4)
- a compartment still holds **one size only**
- a trolley still holds **one film size only** (rule H4)
- recut and CPI still work compartment by compartment (rules L2, L3)

So a trolley may carry batch A in compartments 1–3 and batch B in compartments
4–5, and **never** a third batch.

```
FUNCTION can_combine(a, b, allow_cross_batch):
    IF NOT a.needs_trolleys OR NOT b.needs_trolleys:  RETURN FALSE
    IF a.mo    != b.mo:        RETURN FALSE      # cond 2 — unchanged
    IF a.color != b.color:     RETURN FALSE      # cond 4 — unchanged
    IF a.component != b.component: RETURN FALSE  # cond 4 — unchanged
    IF a.film  != b.film:      RETURN FALSE      # cond 5 — unchanged
    IF a.batch != b.batch AND NOT allow_cross_batch:
        RETURN FALSE                             # cond 3 — RELAXED HERE
    IF trolleys_needed(combine(a, b)) > 4:
        RETURN FALSE                             # cond 7 — unchanged (H8)
    RETURN TRUE
```

### Compartment merging

When the two tables share a batch, their pieces of the same size **merge** into
one compartment if the total is ≤ 150 (Panel Loading Logic rule 2). When the
batches differ, compartments stay separate — the saving comes from sharing the
*trolley*, not the compartment.

```
FUNCTION combine(a, b):
    IF a.batch == b.batch:
        RETURN compartments_for(a.pieces + b.pieces)     # merged
    ELSE:
        RETURN compartments_for(a.pieces)
             + compartments_for(b.pieces)                # side by side
```

### Display requirement

Rule L3 already requires compartment-level information. With two batches on one
trolley this stops being optional: the operator, CPI and recut must all be able
to see **which batch is in which compartment**. If the system can only show
batch at trolley level, change 2 cannot ship.

---

## 4. CHANGE 3 — WIP hold and recall

This is the largest single gain and the one with a real open question attached.

### What happens today

Condition 9: a trolley may only wait if the cutting machine never leaves the
workstation. In practice the cutting machine travels between 2–3 spreading
machines constantly, so the trolley almost never gets to wait. It leaves
part-filled and is gone for the whole round trip.

### What to build

Remove condition 9. Replace it with a **hold-and-recall** cycle:

```
STATE: parked_trolleys — trolleys with free compartments, waiting in CCT WIP
       keyed by (MO, colour, component, film_size)

ON a table finishing cutting:
    # 1. expire anything that has waited too long
    FOR trolley IN parked_trolleys:
        IF now - trolley.parked_at > WIP_HOLD_MINUTES:
            DISPATCH trolley                     # give up, send it on

    # 2. try to fill from what is already parked
    key = (table.mo, table.colour, table.component, table.film_size)
    FOR trolley IN parked_trolleys[key]:
        IF trolley.batches ∪ table.batch has more than 2 batches: SKIP
        RECALL trolley to this workstation
        load as many compartments as fit
        IF trolley now full: DISPATCH it

    # 3. open new trolleys for whatever is left
    WHILE compartments remain unloaded:
        open a new trolley, load up to 5 compartments
        IF it leaves with free compartments AND WIP_HOLD_MINUTES > 0:
            IF count(parked_trolleys) < TROLLEY_BAYS:
                PARK it in CCT WIP, stamp parked_at = now
            ELSE:
                DISPATCH it                      # no room to park
```

### Parameters

| Parameter | Value | Why |
|-----------|-------|-----|
| `WIP_HOLD_MINUTES` | **60** | 1 hour. 2 hours is worth more (75.4% vs 71.3%) but ties up trolleys longer. Start at 60. |
| `TROLLEY_BAYS` | **52** | 13 workstations × 4 positions (rule H7). Never exceeded in any simulated run — but enforce it anyway. |
| `MAX_BATCHES_PER_TROLLEY` | **2** | From change 2. |
| Match key | MO + colour + component + film size | Batch is deliberately **not** in the key. Everything else is. |

### The open question ISD cannot answer alone

The recall in step 2 sends a parked trolley to **whichever workstation** next
cuts a matching table — not necessarily the one it came from. That distinction
is most of the value:

| Recall rule | Utilization | Trolleys/day |
|-------------|-------------|--------------|
| No hold | 65.4% | 182 |
| 1 h, **same workstation only** | 65.9% | 181 |
| 1 h, **any workstation** | **71.3%** | **167** |

Same-workstation-only recall is worth +0.5 points — effectively nothing, because
the same workstation rarely runs a second matching table within the hour.

**So before this is built, someone from Production has to answer: how does a
parked trolley physically get from CCT WIP to a different workstation?** Labour,
AGV, or manual push. If moving it is slow or expensive, the benefit collapses
toward the 65.9% figure and change 3 may not be worth building.

---

## 5. Data the model reads

Everything below comes from the `HaveCut` sheet of PlanPPC.

| Field | Used for |
|-------|----------|
| `Plan Date` | grouping tables into days |
| `Type` | only `B` tables are loaded; `C` adds 10 min setup to its B table |
| `First Table` | `Y` is excluded (rule J2) |
| `Table No` | matching C tables to their B table |
| `MO` | combine condition 2, recall key |
| `Color` | combine condition 4, recall key |
| `Batch No` | combine condition 3 — the one being relaxed |
| `Marker Ratio` | pieces per size → compartments |
| `Act LayerQty` | pieces per size, and spread/cut time |
| `Marker Length` | spread/cut time |

### Two fields the model does NOT have

- **Component.** Not present in the HaveCut export, so the simulation treats
  each table as a single component set. Conditions 1a-4 and 1b-4 must still be
  enforced in the real system. Rule L6 says one component is normally printed
  and front/back usually share Net_Rate, so the effect is probably small — but
  it is unverified.
- **Net_Rate (real film size).** The model uses the H5 mapping
  (90 = XXS–S, 100 = M/L, 110 = XL–4XL). Real Net_Rate varies by style and
  puts *more* sizes on one film, which would make the results **better**, not
  worse. The real system should read Net_Rate, not the H5 mapping.

---

## 6. What to log once it is live

The simulation is only as good as its assumptions. Four numbers would replace
guesses with facts:

1. **Trolley round-trip time** — dispatch from Panel Loading to return. This is
   currently an *estimate* of ~7 days against a 5-day allowance, and it is the
   single number the whole business case turns on.
2. **Compartments loaded per trolley** at dispatch — the direct measurement of
   utilization, which today nobody records.
3. **How often a recall is possible** but the trolley cannot be moved — this
   measures the cost of the open question in section 4.
4. **Combine fire rate** — how many combines actually fire per day, before and
   after. The July run predicted a jump from 37 to 370.

---

## 7. Reproducing the numbers

```bash
python run.py
```

Reads `data/planppc.xlsx`, writes `out/dashboard.html`, `out/results.xlsx`,
`out/results.json`. Every assumption is a named value in `assumptions.py`;
nothing is hard-coded in the model.
