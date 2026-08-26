"""
SCENARIOS
=========
The four headline scenarios are the three changes switched on one at a time,
in the order they would actually be approved. Each row is the previous row
plus one thing — so the table shows what each change is worth ON ITS OWN,
not just what they are worth together.

Also defined here: the sweeps that feed the interactive dashboard, and the
sensitivity tests that show which constraint is really binding.
"""
import assumptions as A
from model import Scenario

# ---------------------------------------------------------------- headline
HEADLINE = [
    Scenario(
        name='S0  Today',
        mo_aware_sequencing=False,
        max_batches=1,
        wip_hold_minutes=0,
    ),
    Scenario(
        name='S1  + same-MO sequencing',
        mo_aware_sequencing=True,       # CHANGE 1
        max_batches=1,
        wip_hold_minutes=0,
    ),
    Scenario(
        name='S2  + 2 batches per trolley',
        mo_aware_sequencing=True,
        max_batches=2,                  # CHANGE 2
        wip_hold_minutes=0,
    ),
    Scenario(
        name='S3  + WIP hold',
        mo_aware_sequencing=True,
        max_batches=2,
        wip_hold_minutes=A.WIP_HOLD_MINUTES,          # CHANGE 3
        hold_any_workstation=A.WIP_HOLD_ANY_WORKSTATION,
    ),
]


# --------------------------------------------------- same WS vs any WS
# The single most important open question in change 3: when a parked trolley
# is called back, may it go to a DIFFERENT workstation, or only its own?
HOLD_VARIANTS = [
    Scenario(name='No hold', mo_aware_sequencing=True, max_batches=2,
             wip_hold_minutes=0),
    Scenario(name='1 h · same workstation only', mo_aware_sequencing=True,
             max_batches=2, wip_hold_minutes=60, hold_any_workstation=False),
    Scenario(name='1 h · any workstation', mo_aware_sequencing=True,
             max_batches=2, wip_hold_minutes=60, hold_any_workstation=True),
    Scenario(name='2 h · same workstation only', mo_aware_sequencing=True,
             max_batches=2, wip_hold_minutes=120, hold_any_workstation=False),
    Scenario(name='2 h · any workstation', mo_aware_sequencing=True,
             max_batches=2, wip_hold_minutes=120, hold_any_workstation=True),
]


# ------------------------------------------------------------- the sweep
# Every combination the dashboard sliders can land on. Fleet size and cycle
# days are NOT swept — they are pure arithmetic on trolleys-per-day, so the
# dashboard computes those live without needing a pre-computed result.
SWEEP_HOLD_MINUTES = [0, 30, 60, 90, 120, 180, 240]
SWEEP_MAX_BATCHES = [1, 2, 3]
SWEEP_MO_AWARE = [False, True]
SWEEP_ANY_WORKSTATION = [False, True]


def sweep_key(mo_aware, max_batches, hold_minutes, any_workstation) -> str:
    """Stable id shared between the Python sweep and the dashboard's lookup."""
    if hold_minutes == 0:
        any_workstation = True          # meaningless when nothing is held
    return f'{int(mo_aware)}|{max_batches}|{hold_minutes}|{int(any_workstation)}'


def sweep_scenarios() -> dict:
    """-> {key: Scenario} for every reachable slider combination."""
    out = {}
    for mo_aware in SWEEP_MO_AWARE:
        for max_batches in SWEEP_MAX_BATCHES:
            for hold in SWEEP_HOLD_MINUTES:
                for any_ws in SWEEP_ANY_WORKSTATION:
                    key = sweep_key(mo_aware, max_batches, hold, any_ws)
                    if key in out:
                        continue
                    out[key] = Scenario(
                        name=key,
                        mo_aware_sequencing=mo_aware,
                        max_batches=max_batches,
                        wip_hold_minutes=hold,
                        hold_any_workstation=any_ws,
                    )
    return out
