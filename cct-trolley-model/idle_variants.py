"""
IDLE-TIME VARIANTS
==================
Regenerates the two tables in `IDLE_TIME.md` — the per-cut-group breakdown in
section 3 and the options list in section 4 — and prints them as markdown,
ready to paste. The bold on the emphasised cells is emitted too, so a paste
does not need it re-applied by hand.

They exist here because they used to come from throwaway scripts, so the two
numbers the idle-time case actually turns on could not be reproduced from the
repo. Everything below reads `model.py` and `assumptions.py` directly; nothing
is re-derived by hand.

    python idle_variants.py

Measured on the S0 sequencing (today's planner) across every plan date in the
data, so it lines up with the rest of the model. This script only prints —
it writes nothing to `out/`.
"""
import contextlib

import assumptions as A
import model

MO_AWARE = False        # S0 — today's planner. IDLE_TIME.md quotes S0 throughout.

# A cut group's row is bolded once its cutter is saturated — that is the point
# section 3 makes, and at 90% it picks out 24MC4 and 24MC5 and nothing else
# (the next busiest is 24MC2 at 82%). Emitted as markdown so the printed table
# really is ready to paste, emphasis and all.
SATURATED_CUTTER_PCT = 90


# =====================================================================
# The routing what-ifs
#
# These are WHAT-IFS FOR THIS ANALYSIS ONLY. Rule F8 as written gives two
# spreading machines a second cutting machine; the variants below widen that
# and are switched in around a single call, then switched back. Nothing else
# in the repo runs with them.
# =====================================================================
FLEX_TODAY = dict(A.FLEXIBLE_CUT)

# Rule F8's own pattern, extended: the LAST spreading machine of a cut group may
# also be served by the NEXT group's cutter. F8 already does exactly that for
# 24-03 (last of 24MC1 -> 24MC2) and 24-05 (last of 24MC2 -> 24MC3). Applying
# the same shape to the two saturated groups gives 24-10 (last of 24MC4) a call
# on 24MC5, and 24-13 (last of 24MC5) a call on 24MC1 — the numbering wraps,
# because there is no 24MC6.
#
# The previous version of IDLE_TIME.md quoted a "24-10 and 24-13 borrow a
# neighbour" row but never recorded which cutter they borrowed, so its figures
# cannot be checked. These are the ones that stand.
FLEX_NEIGHBOUR = dict(FLEX_TODAY)
FLEX_NEIGHBOUR['24-10'] = ['24MC4', '24MC5']
FLEX_NEIGHBOUR['24-13'] = ['24MC5', '24MC1']

# Any cutting machine may serve any spreading machine.
FLEX_ANY = {m: list(A.CUT_GROUPS) for m in model.SPREADERS}


@contextlib.contextmanager
def routing(flexible_cut):
    """Run the block with a different F8 routing, then put F8 back.

    `model.run_timeline` reads `A.FLEXIBLE_CUT` at call time, so swapping the
    module attribute is enough. PRIMARY_CUT is built from CUT_GROUPS and does
    not move.
    """
    original = A.FLEXIBLE_CUT
    A.FLEXIBLE_CUT = flexible_cut
    try:
        yield
    finally:
        A.FLEXIBLE_CUT = original


# =====================================================================
# One measurement: a table length and a routing, over every plan date
# =====================================================================
def measure(days: dict, metres: float, flexible_cut: dict) -> dict:
    """-> per-day averages plus the per-cut-group breakdown.

    Blocked and spreading minutes are attributed to the cut group the SPREADING
    machine belongs to — those are the machines named in the "Spreaders" column.
    Cutter-busy minutes are attributed to the cutter that actually ran the
    table, which under a flexible routing need not be its own group's.
    """
    groups = list(A.CUT_GROUPS)
    cutter_busy = {c: 0.0 for c in groups}
    blocked_by_group = {c: 0.0 for c in groups}
    spread_by_group = {c: 0.0 for c in groups}
    work = blocked = last_cut = 0.0
    machines_over = machine_days = 0

    with routing(flexible_cut):
        for date in sorted(days):
            # run_timeline stamps the tasks, so every variant gets its own copies
            tasks = [dict(t) for t in days[date]]
            plan = model.sequence(tasks, MO_AWARE)
            spreading, _ = model.run_timeline(plan, metres * A.YARDS_PER_METRE)

            work += sum(t['spread_minutes'] for t in tasks)
            blocked += spreading['blocked_minutes']
            machines_over += spreading['machines_over']
            machine_days += len(model.SPREADERS)
            last_cut += max(t['cut_end'] for t in tasks)

            for t in tasks:
                group = model.PRIMARY_CUT[t['machine']]
                cutter_busy[t['cutter']] += t['cut_minutes']
                blocked_by_group[group] += t['blocked_minutes']
                spread_by_group[group] += t['spread_minutes']

    n = len(days)
    return {
        'days': n,
        'work': work / n,
        'blocked': blocked / n,
        'over_pct': 100 * machines_over / machine_days,
        'last_cut': last_cut / n,
        'cutter_busy': {c: v / n for c, v in cutter_busy.items()},
        'blocked_by_group': {c: v / n for c, v in blocked_by_group.items()},
        'spread_by_group': {c: v / n for c, v in spread_by_group.items()},
    }


def bold(cell: str) -> str:
    return '**%s**' % cell


def clock(minutes_from_shift_start: float) -> str:
    """The model's clock starts at 07:15, the floor's at midnight.

    Round to the whole minute BEFORE splitting, so a value like 1419.7 carries
    into the hour instead of printing 23:60. `dashboard.py`'s `hhmm` still
    rounds after the split and has the same latent bug; it is left alone on
    purpose, so the two are only out of step on inputs neither one sees today.
    """
    absolute = round(minutes_from_shift_start + A.SHIFT_START_MINUTE) % 1440
    return '%02d:%02d' % (absolute // 60, absolute % 60)


# =====================================================================
# The two tables
# =====================================================================
def section_2(base: dict):
    print('## 2. What it costs\n')
    print('| | Per day, across %d spreading machines |' % len(model.SPREADERS))
    print('|---|---|')
    print('| Actual spreading work | %s min |' % f'{base["work"]:,.0f}')
    print('| Lost to blocking | **%s min** — %.0f machine-hours |'
          % (f'{base["blocked"]:,.0f}', base['blocked'] / 60))
    print('| Machine-days over their staffed window | **%.0f%%** |' % base['over_pct'])
    print('| Last cut of the day finishes | %s |' % clock(base['last_cut']))


def section_3(base: dict):
    print('\n## 3. Where it concentrates — and why\n')
    print('| Cut group | Spreaders | Cutter busy | Blocked / day | Spreading / day | Blocked / work |')
    print('|---|---|---|---|---|---|')
    for group, spreaders in A.CUT_GROUPS.items():
        busy = 100 * base['cutter_busy'][group] / model.CUTTER_MINUTES[group]
        lost = base['blocked_by_group'][group]
        did = base['spread_by_group'][group]
        nights = ' *(runs nights)*' if group in A.NIGHT_SHIFT_CUTTERS else ''
        # the *(runs nights)* aside sits outside the bold, or the italics nest
        b = bold if busy >= SATURATED_CUTTER_PCT else str
        print('| %s | %s | %s%s | %s | %s | %s |'
              % (b(group), b('%d' % len(spreaders)), b('%.0f%%' % busy), nights,
                 b(f'{lost:,.0f} min'), b(f'{did:,.0f} min'),
                 b('%.0f%%' % (100 * lost / did))))


def section_4(days: dict):
    metres = A.SPREADING_TABLE_LENGTH_M
    # The last column is the emphasis the document gives the row: the two
    # recommendations carry bold on their figures as well as their label.
    # It is an editorial choice, so it is stated here rather than derived.
    variants = [
        ('**Today** — %.1f m' % metres,           metres, FLEX_TODAY,     '—',                False),
        ('24-10 and 24-13 borrow a neighbour',    metres, FLEX_NEIGHBOUR, 'a routing rule',   False),
        ('**Any cutter may serve any spreader**', metres, FLEX_ANY,       'a routing rule',   True),
        ('Table to 24 m',                         24,     FLEX_TODAY,     'floor space',      False),
        ('Table to 24 m + neighbour routing',     24,     FLEX_NEIGHBOUR, 'both',             False),
        ('**Table to 24 m + any cutter**',        24,     FLEX_ANY,       'both',             True),
        ('Table to 27 m + any cutter',            27,     FLEX_ANY,       'both, more space', False),
    ]
    print('\n## 4. What fixes it\n')
    print('| Change | Blocked/day | Over window | Cost |')
    print('|---|---|---|---|')
    for label, length, flex, cost, emphasised in variants:
        r = measure(days, length, flex)
        b = bold if emphasised else str
        print('| %s | %s | %s | %s |'
              % (label, b(f'{r["blocked"]:,.0f}'), b('%.0f%%' % r['over_pct']), cost))


def main():
    days = model.load_days()
    base = measure(days, A.SPREADING_TABLE_LENGTH_M, FLEX_TODAY)
    print('# IDLE_TIME.md — regenerated from %d plan dates, %d tables, S0 sequencing\n'
          % (base['days'], sum(len(t) for t in days.values())))
    section_2(base)
    section_3(base)
    section_4(days)


if __name__ == '__main__':
    main()
