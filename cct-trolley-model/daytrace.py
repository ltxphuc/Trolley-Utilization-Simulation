"""
THE TRACE
=========
The headline numbers are pooled over 20 plan dates. This module exports the
detail underneath them — one plan date at a time, table by table — so the
dashboard's Simulation tab can draw the day that produced them:

    the Job Sequence as a Gantt          (which table, which machine, when)
    the same day loaded onto trolleys    (which compartment, which film)

Two things are exported per day, once for each sequencing rule:

    order  {machine: [task index, ...]}   the queue, in spreading order.
                                          Adjacency lives here — it is what
                                          change 1 creates and what the
                                          combine rule can act on.
    time   {task index: [spread_start, spread_end, cut_start, cut_end, cutter]}

The trolley maths is NOT exported. The dashboard recomputes stage 4 in the
browser, because the Net_Rate scheme has to be switchable and pre-computing
every scheme would multiply the payload. `expected` is the guard on that port:
it carries the utilization Python gets for the same day and settings, and the
page compares its own answer against it in view of the reader.
"""
from __future__ import annotations

import datetime

import assumptions as A
import scenarios as S
from model import Scenario, load_trolleys, run_timeline, sequence

MODES = (('today', False), ('mo_aware', True))

# The spreading table as it is, and the two extensions the idle-time analysis
# costs out. The sequence is unaffected by table length; only the timeline is.
TABLE_LENGTHS_M = (A.SPREADING_TABLE_LENGTH_M, 24.0, 27.0)


def _metres_key(metres: float) -> str:
    """'21.2' — the key the dashboard looks a table length up by."""
    return f'{metres:g}'

# Order of the fields in a task record. The dashboard reads by index, so this
# tuple and the JS `TASK_FIELDS` constant must stay in step.
TASK_FIELDS = (
    'table_no', 'mo', 'style', 'color', 'batch', 'lot',
    'layers', 'marker_length', 'spread_minutes', 'cut_minutes',
    'pieces_by_size', 'needs_trolleys',
    'has_pattern', 'has_fabric', 'batch_first_offset_minutes', 'is_batch_last',
    'spread_done_minutes',
)


def _minutes_into_day(when, day) -> float | None:
    """Pull Date (actual finished spreading) as minutes from midnight of the
    plan date. Negative means it finished before the day it was planned for;
    over 1440 means it ran late, which is the common case."""
    if when is None:
        return None
    midnight = datetime.datetime.combine(day, datetime.time.min)
    return round((when - midnight).total_seconds() / 60, 1)


def _record(task: dict, day) -> list:
    return [
        task['table_no'], task['mo'], task['style'], task['color'],
        task['batch'], task['lot'],
        task['layers'], round(task['marker_length'], 2),
        round(task['spread_minutes'], 1), round(task['cut_minutes'], 1),
        # NOT sorted. compartments_for() walks this dict in order, so the order
        # decides which film width opens a trolley first — which matters once
        # the 52 trolley bays (H7) are full. Sorting here silently changes the
        # answer on busy days.
        dict(task['pieces_by_size']),
        int(task['needs_trolleys']),
        int(task['has_pattern']), int(task['has_fabric']),
        task['batch_first_offset_minutes'], int(task['is_batch_last']),
        _minutes_into_day(task['spread_done_at'], day),
    ]


def _expected(plan: dict, mo_aware: bool) -> dict:
    """What Python gets for this day at every setting the tab can reach.

    The sequence and the timeline depend only on `mo_aware`, so the plan is
    built once and only the loading stage is re-run.
    """
    out = {}
    for max_batches in S.SWEEP_MAX_BATCHES:
        for hold in S.SWEEP_HOLD_MINUTES:
            for any_ws in S.SWEEP_ANY_WORKSTATION:
                key = S.sweep_key(mo_aware, max_batches, hold, any_ws)
                if key in out:
                    continue
                loading = load_trolleys(plan, Scenario(
                    name=key,
                    mo_aware_sequencing=mo_aware,
                    max_batches=max_batches,
                    wip_hold_minutes=hold,
                    hold_any_workstation=any_ws,
                ))
                comps, trolleys = loading['compartments'], loading['trolleys']
                out[key] = [
                    round(100 * comps / (A.TROLLEY_COMPARTMENTS * trolleys), 2) if trolleys else 0.0,
                    trolleys,
                    comps,
                    loading['combines'],
                ]
    return out


def build_trace(days: dict, skipped: dict | None = None) -> dict:
    """-> the whole payload the Simulation tab reads."""
    skipped = skipped or {}
    out = {
        'fields': list(TASK_FIELDS),
        'dates': [str(d) for d in sorted(days)],
        'days': {},
    }

    for date in sorted(days):
        tasks = days[date]
        day = {
            'tasks': [_record(t, date) for t in tasks],
            'skipped': skipped.get(date, 0),
            'seq': {},
        }

        for mode, mo_aware in MODES:
            order, by_buffer = {}, {}

            for metres in TABLE_LENGTHS_M:
                # sequence() and run_timeline() both mutate the task dicts, so
                # every run gets its own copies — exactly as model.run() does.
                copies = [dict(t) for t in tasks]
                for i, t in enumerate(copies):
                    t['_i'] = i
                plan = sequence(copies, mo_aware)
                run_timeline(plan, table_length=metres * A.YARDS_PER_METRE)

                time = {}
                for machine, queue in plan.items():
                    if not queue:
                        continue
                    # The sequence does not depend on the buffer — only the
                    # timing does — so the queue is recorded once.
                    order[machine] = [t['_i'] for t in queue]
                    for t in queue:
                        time[t['_i']] = [
                            round(t['spread_start'], 1), round(t['spread_end'], 1),
                            round(t['cut_start'], 1),
                            # cut_end is NOT rounded. The dashboard sorts loading
                            # events by it and measures the WIP hold against it,
                            # so rounding can reorder two near-simultaneous
                            # tables and cost a trolley. The rest is for drawing.
                            t['cut_end'],
                            t['cutter'],
                        ]
                by_buffer[_metres_key(metres)] = {
                    'time': time,
                    'expected': _expected(plan, mo_aware),
                    'blocked': round(sum(t['blocked_minutes'] for t in copies), 1),
                }

            day['seq'][mode] = {'order': order, 'table': by_buffer}

        out['days'][str(date)] = day

    return out
