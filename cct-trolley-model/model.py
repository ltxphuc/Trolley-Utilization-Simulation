"""
THE MODEL
=========
One day of Central Cutting, simulated end to end, in four stages:

    1. READ      each Plan Date in the HaveCut sheet becomes one day of tasks
    2. SEQUENCE  the planner assigns tasks to spreading machines, in an order
    3. TIME      spreading and cutting run; blocking and idle time fall out
    4. LOAD      cut panels go into trolley compartments; trolleys are counted

Stages 2 and 4 are deliberately separate, and that separation IS the finding:
the current planner (flowchart 3.3a) spreads one fabric batch across the three
machines of a cut group, so two tables that COULD share a trolley almost never
end up next to each other at one workstation — and the loading step can only
combine tables that are already adjacent.

Every tunable lives in assumptions.py. Nothing is hard-coded here.
"""
from __future__ import annotations

import collections
import datetime
import math
import statistics
from dataclasses import dataclass

import openpyxl

import assumptions as A

PRIMARY_CUT = {m: c for c, ms in A.CUT_GROUPS.items() for m in ms}
SPREADERS = list(PRIMARY_CUT)


# =====================================================================
# THE SHIFTS
# Every time is minutes from 07:15. A machine can only work inside its
# shift, and not through a break, so the timeline has to step over those
# windows rather than run continuously.
# =====================================================================
def working_intervals(nights: bool) -> list:
    """-> [(start, end), ...] the machine can actually work in, in order."""
    start, end = A.NIGHT_SHIFT if nights else A.DAY_SHIFT
    start = min(start, A.DAY_SHIFT[0])          # night machines work the day too
    breaks = list(A.DAY_BREAKS) + (list(A.NIGHT_BREAKS) if nights else [])
    if not A.BREAKS_STOP_MACHINES:
        breaks = []

    spans, cursor = [], start
    for b_start, b_end in sorted(breaks):
        if b_end <= cursor or b_start >= end:
            continue
        if b_start > cursor:
            spans.append((cursor, min(b_start, end)))
        cursor = max(cursor, b_end)
    if cursor < end:
        spans.append((cursor, end))
    return spans


SPREADER_SHIFT = {m: working_intervals(m in A.NIGHT_SHIFT_SPREADERS) for m in SPREADERS}
CUTTER_SHIFT = {c: working_intervals(c in A.NIGHT_SHIFT_CUTTERS) for c in A.CUT_GROUPS}

# Staffed minutes, net of breaks — derived, never hard-coded, so the planning
# heuristic and the Gantt can never disagree about how long a machine runs.
MACHINE_MINUTES = {m: sum(e - s for s, e in SPREADER_SHIFT[m]) for m in SPREADERS}
CUTTER_MINUTES = {c: sum(e - s for s, e in CUTTER_SHIFT[c]) for c in A.CUT_GROUPS}
SHIFT_END = max(max(e for _, e in spans) for spans in SPREADER_SHIFT.values())


def _advance(spans: list, t: float) -> float:
    """The first working instant at or after t."""
    for s, e in spans:
        if t < s:
            return s
        if t < e:
            return t
    return t                                    # past the end of the shift


def occupy(spans: list, start: float, minutes: float) -> tuple:
    """Run `minutes` of work from `start`, pausing for anything non-working.

    -> (actually started, finished). Work past the end of the shift runs on
    rather than being lost — the day simply overruns, which is the thing the
    idle-time analysis is about.
    """
    t = _advance(spans, start)
    began, left = t, minutes
    for s, e in spans:
        if left <= 0:
            break
        if e <= t:
            continue
        t = max(t, s)
        room = e - t
        if room >= left:
            return began, t + left
        left -= room
        t = e
    return began, t + left                      # overran the shift


# =====================================================================
# A scenario is just the three changes, switched on or off.
# =====================================================================
@dataclass(frozen=True)
class Scenario:
    name: str
    mo_aware_sequencing: bool = False   # CHANGE 1
    max_batches: int = 1                # CHANGE 2  (1 = today, 2 = proposed)
    wip_hold_minutes: int = 0           # CHANGE 3  (0 = off)
    hold_any_workstation: bool = True

    @property
    def cross_batch(self) -> bool:
        return self.max_batches >= 2


# =====================================================================
# 1. READ
# =====================================================================
def parse_marker_ratio(raw) -> dict:
    """'S/2,M/3,L/2' -> {'S': 2, 'M': 3, 'L': 2}"""
    out = {}
    for part in str(raw or '').split(','):
        if '/' not in part:
            continue
        size, count = part.rsplit('/', 1)
        try:
            out[size.strip()] = int(float(count))
        except ValueError:
            pass
    return out


def _as_datetime(value):
    """Excel gives datetimes; anything else is treated as missing."""
    return value if isinstance(value, datetime.datetime) else None


def load_days(path: str | None = None, with_stats: bool = False):
    """-> {date: [task, ...]} — one entry per Plan Date.

    With `with_stats`, also returns {date: rows skipped} so the dashboard can
    say how many of the day's planned tables the model actually carries.
    """
    wb = openpyxl.load_workbook(path or A.DATA_FILE, read_only=True, data_only=True)
    rows_iter = wb[A.DATA_SHEET].iter_rows(min_row=1, values_only=True)
    header = next(rows_iter)
    col = {name: i for i, name in enumerate(header)}
    rows = [r for r in rows_iter if r[0]]

    # C tables share a physical table with a B table and add setup time (G3/I3).
    c_tables = {
        (r[col['Plan Date']].date(), r[col['Table No']])
        for r in rows
        if r[col['Type']] == 'C' and r[col['Plan Date']]
    }

    days = collections.defaultdict(list)
    skipped = collections.Counter()
    for r in rows:
        plan_date = _as_datetime(r[col['Plan Date']])
        if r[col['Type']] != 'B' or r[col['First Table']] == 'Y':
            if plan_date:
                skipped[plan_date.date()] += 1                     # J2
            continue
        if not plan_date:
            continue
        ratio = parse_marker_ratio(r[col['Marker Ratio']])
        layers = r[col['Act LayerQty']] or 0
        marker_len = r[col['Marker Length']] or 0
        if not ratio or layers <= 0 or marker_len <= 0:
            skipped[plan_date.date()] += 1
            continue

        day = plan_date.date()
        # J3 — only universal-size markers get trolley accounting. Kids and
        # number-size markers still occupy machines, so they stay in the
        # timeline; they simply carry no compartments.
        universal = all(s in A.FILM_SIZE_BY_GARMENT_SIZE for s in ratio)
        setup = A.C_TABLE_EXTRA_MINUTES if (day, r[col['Table No']]) in c_tables else 0

        days[day].append({
            'table_no': r[col['Table No']],
            'mo': r[col['MO']],
            'style': r[col['STYLE']],
            'color': r[col['Color']],
            'lot': r[col['Lot']],
            'batch': r[col['Batch No']],
            'layers': layers,
            'marker_length': float(marker_len),
            'needs_trolleys': universal,
            'pieces_by_size': {s: n * layers for s, n in ratio.items()} if universal else {},
            'spread_minutes': layers * A.SPREAD_MIN_PER_LAYER_PER_YARD * float(marker_len) + setup,
            'cut_minutes': layers * A.CUT_MIN_PER_LAYER_PER_YARD * float(marker_len),
            # ---- readiness inputs (see "Task readiness statuses" in README) ----
            'plan_date': day,
            'has_pattern': _as_datetime(r[col['Marker Date']]) is not None,
            'has_fabric': bool(r[col['Lot']]) and bool(r[col['Batch No']]),
            # Pull Date is the ACTUAL finished-spreading timestamp, not a plan.
            'spread_done_at': _as_datetime(r[col['Pull Date']]),
        })

    days = dict(days)
    _stamp_batch_readiness(days)
    return (days, dict(skipped)) if with_stats else days


def _stamp_batch_readiness(days: dict):
    """Derive the two batch-level readiness flags, in place.

    Neither has a source column, so both are inferred:

    `batch_first_planned`  the earliest Plan Date any table of this batch
                      appears on. Fabric arrival is not in the export, so this
                      anchors the relax simulation: the fabric is taken to be
                      issued FABRIC_ISSUE_LEAD_HOURS before this, and a table is
                      ready once its scheduled spread start is RELAX_HOURS past
                      that. Whether a table is relaxed therefore depends on the
                      sequence, and is worked out per scenario — not here.

    `is_batch_last`   the table that spreads the last yards of a batch — the
                      one that may stretch-spread. Taken as the batch's final
                      table by actual finished-spreading time.
    """
    first_plan, last_table = {}, {}
    for date, tasks in days.items():
        for t in tasks:
            batch = t['batch']
            if batch not in first_plan or date < first_plan[batch]:
                first_plan[batch] = date
            done = t['spread_done_at']
            if done is not None:
                previous = last_table.get(batch)
                if previous is None or done > previous[0]:
                    last_table[batch] = (done, t)

    for tasks in days.values():
        for t in tasks:
            arrived = first_plan[t['batch']]
            t['batch_first_planned'] = arrived
            # minutes from midnight of THIS table's plan date back to midnight of
            # the day its batch first appeared. Zero or negative.
            t['batch_first_offset_minutes'] = (
                datetime.datetime.combine(arrived, datetime.time.min)
                - datetime.datetime.combine(t['plan_date'], datetime.time.min)
            ).total_seconds() / 60
            t['is_batch_last'] = last_table.get(t['batch'], (None, None))[1] is t


# =====================================================================
# COMPARTMENT MATHS  (H1, H3, H4, H5)
# =====================================================================
def compartments_for(pieces_by_size: dict) -> dict:
    """-> {film_size: [pieces in each compartment]}

    A compartment holds one size on one film, up to COMPARTMENT_CAP.
    Sizes on the same film may not share a compartment unless the tables
    are combined (see combined_compartments)."""
    out = collections.defaultdict(list)
    for size, qty in pieces_by_size.items():
        film = A.FILM_SIZE_BY_GARMENT_SIZE[size]
        full, remainder = divmod(qty, A.COMPARTMENT_CAP)
        out[film].extend([A.COMPARTMENT_CAP] * full)
        if remainder:
            out[film].append(remainder)
    return out


def trolleys_for(comps: dict) -> int:
    """Compartments of different film sizes may not share a trolley (H4)."""
    return sum(math.ceil(len(v) / A.TROLLEY_COMPARTMENTS) for v in comps.values() if v)


def combined_compartments(a: dict, b: dict) -> dict:
    """Compartments when two tables are loaded together.

    SAME batch      -> their pieces merge, so two part-full compartments of the
                       same size become one (Panel Loading Logic rule 2).
    DIFFERENT batch -> compartments stay separate (H1/H4) because a compartment
                       may only hold one batch — but they share the trolley.
    """
    if a['batch'] == b['batch']:
        merged = collections.Counter(a['pieces_by_size'])
        merged.update(b['pieces_by_size'])
        return compartments_for(merged)

    out = collections.defaultdict(list)
    for table in (a, b):
        for film, comps in compartments_for(table['pieces_by_size']).items():
            out[film].extend(comps)
    return out


def can_combine(a: dict, b: dict, cross_batch: bool):
    """The combine rule. Returns the compartment layout, or None if forbidden.

    Conditions checked here:
      - both tables actually need trolleys                    (J3)
      - same MO                                               (H9)
      - same colour
      - same batch, UNLESS cross_batch is on   <-- CHANGE 2 relaxes this
      - the pair does not need more than 4 trolleys           (H8)
    Adjacency (the tables must be back-to-back at one workstation) is enforced
    by the caller, because it is a property of the sequence, not the pair.
    """
    if not a['needs_trolleys'] or not b['needs_trolleys']:
        return None
    if a['mo'] != b['mo'] or a['color'] != b['color']:
        return None
    if a['batch'] != b['batch'] and not cross_batch:
        return None
    comps = combined_compartments(a, b)
    if trolleys_for(comps) > A.MAX_TROLLEYS_PER_COMBINE:
        return None
    return comps


# =====================================================================
# 2. SEQUENCE
# =====================================================================
def _pick_machine(candidates, load, work):
    """Least-loaded machine that still has staffed room; else least-loaded."""
    room = [m for m in candidates if load[m] + work <= MACHINE_MINUTES[m] * A.MACHINE_FILL_TARGET]
    if room:
        return min(room, key=load.get)
    room = [m for m in SPREADERS if load[m] + work <= MACHINE_MINUTES[m] * A.MACHINE_FILL_TARGET]
    if room:
        return min(room, key=load.get)
    return min(SPREADERS, key=lambda m: load[m] / MACHINE_MINUTES[m])


def sequence(tasks: list, mo_aware: bool) -> dict:
    """-> {machine: [task, ...]} in the order they will be spread."""
    group_load = {c: 0.0 for c in A.CUT_GROUPS}
    machine_load = {m: 0.0 for m in SPREADERS}
    plan = {m: [] for m in SPREADERS}

    if not mo_aware:
        return _sequence_today(tasks, plan, machine_load, group_load)
    return _sequence_mo_aware(tasks, plan, machine_load, group_load)


def _sequence_today(tasks, plan, machine_load, group_load):
    """TODAY (flowchart 3.3a): cluster by MO + colour + batch, then scatter that
    batch across the three machines of one cut group, one table at a time to
    whichever machine is least loaded. Two tables that could share a trolley
    therefore land back-to-back only by accident.

    Assignment used to be a fixed round robin restarting at machines[0] for
    every cluster. Tables are sorted longest-first, so the biggest table of
    every cluster landed on the group's first machine: 24-01 carried 811
    spread-min/day against 24-03's 503 on near-identical table counts."""
    clusters = collections.defaultdict(list)
    for t in tasks:
        clusters[(t['mo'], t['color'], t['batch'])].append(t)

    for group_tasks in sorted(clusters.values(),
                              key=lambda ts: -sum(t['spread_minutes'] for t in ts)):
        cut_group = min(group_load, key=lambda c: group_load[c] / len(A.CUT_GROUPS[c]))
        machines = A.CUT_GROUPS[cut_group]
        for task in sorted(group_tasks, key=lambda t: -t['spread_minutes']):
            machine = _pick_machine(machines, machine_load, task['spread_minutes'])
            plan[machine].append(task)
            machine_load[machine] += task['spread_minutes']
            group_load[cut_group] += task['spread_minutes']
    return plan


def _sequence_mo_aware(tasks, plan, machine_load, group_load):
    """CHANGE 1: cluster by MO + colour, pair tables up BEFORE assigning, and
    put each pair on ONE machine back-to-back.

    Priority order, as specified:
        pass 0 — pair same MO + same batch first
        pass 1 — then pair same MO + different batch
    """
    clusters = collections.defaultdict(list)
    for t in tasks:
        clusters[(t['mo'], t['color'])].append(t)

    for group_tasks in sorted(clusters.values(),
                              key=lambda ts: -sum(t['spread_minutes'] for t in ts)):
        ordered = sorted(group_tasks, key=lambda t: (str(t['batch']), -t['spread_minutes']))
        taken = [False] * len(ordered)
        units = []

        for same_batch_pass in (True, False):
            for i in range(len(ordered)):
                if taken[i]:
                    continue
                for j in range(i + 1, len(ordered)):
                    if taken[j]:
                        continue
                    is_same_batch = ordered[i]['batch'] == ordered[j]['batch']
                    if is_same_batch != same_batch_pass:
                        continue
                    if can_combine(ordered[i], ordered[j], cross_batch=True):
                        units.append([ordered[i], ordered[j]])
                        taken[i] = taken[j] = True
                        break
        units += [[t] for i, t in enumerate(ordered) if not taken[i]]

        cut_group = min(group_load, key=lambda c: group_load[c] / len(A.CUT_GROUPS[c]))
        for unit in sorted(units, key=lambda u: -sum(t['spread_minutes'] for t in u)):
            work = sum(t['spread_minutes'] for t in unit)
            machine = _pick_machine(A.CUT_GROUPS[cut_group], machine_load, work)
            plan[machine].extend(unit)          # the pair stays adjacent HERE
            machine_load[machine] += work
            group_load[cut_group] += work
    return plan


# =====================================================================
# 3. TIME  — run the plan, record blocking, stamp each table's cut-finish
# =====================================================================
def _free_length(lays: list, table_length: float, when: float) -> float:
    """Table length free at `when`.

    Each lay holds its marker length until cutting starts, then gives it back
    linearly as the lay is fed into the cutting machine (G6).
    """
    used = 0.0
    for length, cut_start, cut_end in lays:
        if when >= cut_end:
            continue
        if when <= cut_start or cut_end <= cut_start:
            used += length
        else:
            used += length * (cut_end - when) / (cut_end - cut_start)
    return table_length - used


def _room_at(lays: list, table_length: float, earliest: float, need: float) -> float:
    """When `need` yards of table first come free, at or after `earliest`.

    Free length only rises between lays being added, so it is enough to walk
    the cut start/end boundaries and bisect inside the span that crosses.
    """
    if _free_length(lays, table_length, earliest) >= need:
        return earliest
    marks = sorted(t for _, cs, ce in lays for t in (cs, ce) if t > earliest)
    low = earliest
    for mark in marks:
        if _free_length(lays, table_length, mark) >= need:
            high = mark
            for _ in range(40):
                mid = (low + high) / 2
                if _free_length(lays, table_length, mid) >= need:
                    high = mid
                else:
                    low = mid
            return high
        low = mark
    # A lay longer than the table cannot fit beside anything — wait for a clear
    # table. Markers are ~9 yd against 23 yd of table, so this is a safety net.
    return max([earliest] + [ce for _, _, ce in lays])


def run_timeline(plan: dict, table_length: float = None) -> tuple:
    """Simulates spreading and cutting. Writes 'cut_end' onto every task
    (the loading stage needs it) and returns idle-time aggregates.

    `table_length` overrides the spreading table's usable length in yards,
    which is the buffer between spreading and cutting — see IDLE_TIME.md.
    """
    table_length = A.SPREADING_TABLE_LENGTH if table_length is None else table_length
    spread_free = {m: 0.0 for m in SPREADERS}
    spread_busy = {m: 0.0 for m in SPREADERS}
    spread_blocked = {m: 0.0 for m in SPREADERS}
    cut_free = {c: 0.0 for c in A.CUT_GROUPS}
    cut_busy = {c: 0.0 for c in A.CUT_GROUPS}
    cut_waiting = {c: 0.0 for c in A.CUT_GROUPS}
    at_workstation = {m: [] for m in SPREADERS}
    pointer = {m: 0 for m in SPREADERS}

    while any(pointer[m] < len(plan[m]) for m in SPREADERS):
        machine = min((m for m in SPREADERS if pointer[m] < len(plan[m])),
                      key=lambda m: spread_free[m])
        task = plan[machine][pointer[machine]]
        pointer[machine] += 1

        start = spread_free_before = spread_free[machine]
        # G6 — cannot start until enough table has come free. The lay in front
        # gives its length back gradually as the cutter eats it, so this is a
        # length test, not a count of tables.
        start = _room_at(at_workstation[machine], table_length, start,
                         task['marker_length'])
        blocked = start - spread_free_before          # G6 only
        # ...and cannot start outside the shift, or during a break. That wait is
        # NOT blocking — the machine is unstaffed, not starved — so it is counted
        # separately and never enters the blocked percentage.
        start, spread_end = occupy(SPREADER_SHIFT[machine], start, task['spread_minutes'])
        spread_blocked[machine] += blocked
        spread_busy[machine] += task['spread_minutes']
        spread_free[machine] = spread_end

        cutter = min(A.FLEXIBLE_CUT.get(machine, [PRIMARY_CUT[machine]]),
                     key=lambda c: cut_free[c])
        cut_waiting[cutter] += max(0.0, spread_end - cut_free[cutter])
        cut_start, cut_end = occupy(CUTTER_SHIFT[cutter],
                                    max(spread_end, cut_free[cutter]),
                                    task['cut_minutes'])
        cut_busy[cutter] += task['cut_minutes']
        cut_free[cutter] = cut_end

        at_workstation[machine].append((task['marker_length'], cut_start, cut_end))
        task['cut_end'] = cut_end            # <-- the loading stage reads this
        # The rest is for the Gantt only; nothing in the model reads them.
        task['machine'] = machine
        task['cutter'] = cutter
        task['spread_start'] = start
        task['spread_end'] = spread_end
        task['cut_start'] = cut_start
        task['blocked_minutes'] = blocked

    def aggregate(busy, blocked, keys, staffed_by_key, free_at):
        total_busy = sum(busy[k] for k in keys)
        total_blocked = sum(blocked[k] for k in keys)
        occupied = sum(busy[k] + blocked[k] for k in keys)
        staffed = sum(staffed_by_key[k] for k in keys)
        over = sum(max(0.0, busy[k] + blocked[k] - staffed_by_key[k]) for k in keys)
        return {
            'blocked_pct': 100 * total_blocked / occupied if occupied else 0.0,
            'blocked_minutes': total_blocked,
            'busy_minutes': total_busy,
            'staffed_idle_pct': 100 * (1 - total_busy / staffed) if staffed else 0.0,
            # work that did not fit in the staffed window — the cost of blocking,
            # in the one unit the floor actually feels
            'overrun_minutes': over,
            'machines_over': sum(1 for k in keys
                                 if busy[k] + blocked[k] > staffed_by_key[k]),
            'makespan_hours': max(free_at.values()) / 60 if free_at else 0.0,
        }

    return (aggregate(spread_busy, spread_blocked, SPREADERS,
                      MACHINE_MINUTES, spread_free),
            aggregate(cut_busy, cut_waiting, list(A.CUT_GROUPS),
                      CUTTER_MINUTES, cut_free))


# =====================================================================
# 4. LOAD
# =====================================================================
def _loading_events(plan: dict, cross_batch: bool) -> list:
    """Walk each workstation's sequence and combine adjacent tables where the
    rule allows. -> [(cut_end, table, compartments, batches, machine)] in the
    order panels actually arrive at the loading area."""
    events = []
    for machine, seq in plan.items():
        i = 0
        while i < len(seq):
            if not seq[i]['needs_trolleys']:
                i += 1
                continue
            pair = i + 1 < len(seq) and can_combine(seq[i], seq[i + 1], cross_batch)
            if pair:
                comps = combined_compartments(seq[i], seq[i + 1])
                batches = {seq[i]['batch'], seq[i + 1]['batch']}
                when = max(seq[i]['cut_end'], seq[i + 1]['cut_end'])
                table = seq[i]
                i += 2
            else:
                comps = compartments_for(seq[i]['pieces_by_size'])
                batches = {seq[i]['batch']}
                when, table = seq[i]['cut_end'], seq[i]
                i += 1
            events.append((when, table, comps, batches, machine))
    events.sort(key=lambda e: e[0])
    return events


def load_trolleys(plan: dict, scenario: Scenario) -> dict:
    """Fill trolleys. With WIP hold on, a part-filled trolley is parked and may
    be topped up by a later matching table instead of leaving half empty."""
    events = _loading_events(plan, scenario.cross_batch)
    hold = scenario.wip_hold_minutes

    # parked[key] = [[free_compartments, parked_at, {batches on board}], ...]
    parked = collections.defaultdict(list)
    parked_now = lambda: sum(len(v) for v in parked.values())

    compartments_used = trolleys_opened = pieces = 0
    combines = 0
    waits, blocked_by_space = [], 0

    for when, table, comps, batches, machine in events:
        if len(batches) > 1:
            combines += 1

        # Send away anything that has waited its allowance.
        for key in list(parked):
            still_waiting = []
            for trolley in parked[key]:
                if when - trolley[1] <= hold:
                    still_waiting.append(trolley)
                else:
                    waits.append(when - trolley[1])
            parked[key] = still_waiting

        for film, compartment_list in comps.items():
            if not compartment_list:
                continue
            compartments_used += len(compartment_list)
            pieces += sum(compartment_list)

            key = (table['mo'], table['color'], film)
            if not scenario.hold_any_workstation:
                key += (machine,)               # may only return to its own WS

            need = len(compartment_list)

            # (a) top up trolleys already parked and waiting
            for trolley in parked[key]:
                if need == 0:
                    break
                would_carry = trolley[2] | batches
                if len(would_carry) > A.MAX_BATCHES_PER_TROLLEY:
                    continue                    # would put a 3rd batch on board
                take = min(trolley[0], need)
                if take == 0:
                    continue
                trolley[0] -= take
                trolley[2] = would_carry
                need -= take
            parked[key] = [t for t in parked[key] if t[0] > 0]

            # (b) open fresh trolleys for whatever is left
            while need > 0:
                take = min(A.TROLLEY_COMPARTMENTS, need)
                need -= take
                trolleys_opened += 1
                spare = A.TROLLEY_COMPARTMENTS - take
                if spare and hold > 0:
                    if parked_now() < A.TROLLEY_BAYS:
                        parked[key].append([spare, when, set(batches)])
                    else:
                        blocked_by_space += 1

    return {
        'compartments': compartments_used,
        'trolleys': trolleys_opened,
        'pieces': pieces,
        'combines': combines,
        'avg_wait_hours': statistics.mean(waits) / 60 if waits else 0.0,
        'blocked_by_space': blocked_by_space,
    }


# =====================================================================
# RUN
# =====================================================================
def run_day(tasks: list, scenario: Scenario) -> dict:
    plan = sequence(tasks, scenario.mo_aware_sequencing)
    spreading, cutting = run_timeline(plan)
    loading = load_trolleys(plan, scenario)

    comps, trolleys = loading['compartments'], loading['trolleys']
    return {
        'tasks': len(tasks),
        'combines': loading['combines'],
        'compartments': comps,
        'trolleys': trolleys,
        'pieces': loading['pieces'],
        # H6 — this is THE headline metric
        'trolley_utilization_pct': 100 * comps / (A.TROLLEY_COMPARTMENTS * trolleys) if trolleys else 0.0,
        'compartment_fill_pct': 100 * loading['pieces'] / (A.COMPARTMENT_CAP * comps) if comps else 0.0,
        'pieces_per_trolley': loading['pieces'] / trolleys if trolleys else 0.0,
        'spreading_blocked_pct': spreading['blocked_pct'],
        'cutting_blocked_pct': cutting['blocked_pct'],
        'spreading_makespan_hours': spreading['makespan_hours'],
        'spreading_blocked_minutes': spreading['blocked_minutes'],
        'spreading_overrun_minutes': spreading['overrun_minutes'],
        'machines_over_window': spreading['machines_over'],
        'avg_wait_hours': loading['avg_wait_hours'],
        'blocked_by_space': loading['blocked_by_space'],
    }


def run(scenario: Scenario, days: dict) -> dict:
    """Run one scenario over every plan date. -> aggregate + per-day detail."""
    per_day = {}
    for date in sorted(days):
        # sequence() mutates task dicts (it stamps cut_end), so hand each
        # scenario its own copies — otherwise runs contaminate each other.
        tasks = [dict(t) for t in days[date]]
        per_day[str(date)] = run_day(tasks, scenario)

    avg = lambda k: statistics.mean(d[k] for d in per_day.values())
    total_comps = sum(d['compartments'] for d in per_day.values())
    total_trolleys = sum(d['trolleys'] for d in per_day.values())

    return {
        'scenario': scenario.name,
        'settings': {
            'mo_aware_sequencing': scenario.mo_aware_sequencing,
            'max_batches': scenario.max_batches,
            'wip_hold_minutes': scenario.wip_hold_minutes,
            'hold_any_workstation': scenario.hold_any_workstation,
        },
        # utilization is pooled over all days, not a mean of daily percentages
        'utilization_pct': 100 * total_comps / (A.TROLLEY_COMPARTMENTS * total_trolleys),
        'trolleys_per_day': total_trolleys / len(per_day),
        'peak_trolleys_in_a_day': max(d['trolleys'] for d in per_day.values()),
        'compartments_per_day': total_comps / len(per_day),
        'pieces_per_trolley': avg('pieces_per_trolley'),
        'spreading_blocked_pct': avg('spreading_blocked_pct'),
        'cutting_blocked_pct': avg('cutting_blocked_pct'),
        'spreading_makespan_hours': avg('spreading_makespan_hours'),
        'spreading_blocked_minutes': avg('spreading_blocked_minutes'),
        'spreading_overrun_minutes': avg('spreading_overrun_minutes'),
        'machines_over_window': avg('machines_over_window'),
        'avg_wait_hours': avg('avg_wait_hours'),
        'blocked_by_space': sum(d['blocked_by_space'] for d in per_day.values()),
        'per_day': per_day,
    }


# =====================================================================
# FLEET ARITHMETIC — no simulation, just multiplication. Kept here so the
# one place that defines "how many trolleys do we need" is in the model.
# =====================================================================
def fleet_required(trolleys_per_day: float, cycle_days: float) -> float:
    """A trolley dispatched today is unavailable for `cycle_days`. So the fleet
    has to cover that many days of dispatches at once."""
    return trolleys_per_day * cycle_days


def longest_sustainable_cycle(trolleys_per_day: float, fleet: int = None) -> float:
    """How slow the round trip can get before the fleet runs dry."""
    return (fleet or A.FLEET_SIZE) / trolleys_per_day
