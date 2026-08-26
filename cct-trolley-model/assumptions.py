"""
ASSUMPTIONS
===========
Every number the model depends on lives here. Change a value, re-run
`python run.py`, and every output updates.

Each entry cites the rule it comes from (RULES.docx section, or the Job
Sequence flowchart). Where a value is an ESTIMATE rather than a measurement,
it says so — those are the ones worth challenging first.
"""

# ---------------------------------------------------------------- the trolley
TROLLEY_COMPARTMENTS = 5      # H3 — compartments on one trolley
COMPARTMENT_CAP = 150         # H1 — max garments in one compartment
MAX_BATCHES_PER_TROLLEY = 2   # floor rule — a trolley may carry 2 fabric
                              # batches in separate compartments, NEVER 3.
                              # Set to 1 to model today's same-batch-only rule.

MAX_TROLLEYS_PER_COMBINE = 4  # H8 — two combined tables may not need >4 trolleys
TROLLEY_BAYS = 52             # H7 — 13 workstations x 4 trolley positions.
                              # Caps how many part-filled trolleys can be
                              # parked and waiting at any one moment.

# --------------------------------------------------------------- the fleet
FLEET_SIZE = 1200             # trolleys the factory owns, total, across every
                              # process from Cutting through to Sewing.

CYCLE_DAYS_ALLOWED = 5        # the lead-time allowance: Relaxing -> Sewing
                              # (1+3+1 days per the process breakdown).

CYCLE_DAYS_ESTIMATED = 7      # <-- ESTIMATE, NOT MEASURED. The requester's own
                              # figure for how long a trolley really takes to
                              # come back to Panel Loading. This single number
                              # decides whether the fleet is short. Measuring it
                              # for one week is the highest-value thing on the
                              # open-items list.

# --------------------------------------------------------------- WIP hold
WIP_HOLD_MINUTES = 60         # how long a part-filled trolley may wait in CCT
                              # WIP for a later matching table. 0 = off
                              # (dispatch immediately, which is today's rule).

WIP_HOLD_ANY_WORKSTATION = True
                              # True  = a parked trolley can be called to
                              #         WHICHEVER workstation next cuts a
                              #         matching table.
                              # False = it may only be topped up by a later
                              #         table at the SAME workstation it left.
                              # This flag is worth ~6 points on its own. The
                              # operational question of HOW the trolley travels
                              # (labour / AGV / manual push) is NOT modelled.

# The match key for topping up a parked trolley. All three must be equal.
# Batches may differ — that is the whole point — but colour and film size
# may not, so a trolley is never mixed across dye lots or film widths.
WIP_HOLD_MATCH_ON = ('mo', 'color', 'film_size')

# ------------------------------------------------------------ film sizes (H5)
# Which film width each garment size is cut on. Sizes on different films
# cannot share a compartment.
FILM_SIZE_BY_GARMENT_SIZE = {
    'XXS':  90, 'XS':  90, 'S':  90,
    'M':   100, 'L':  100,
    'XL':  110, 'XXL': 110, '3XL': 110, '4XL': 110,
}
UNIVERSAL_SIZES = list(FILM_SIZE_BY_GARMENT_SIZE)

# Net_Rate is universal here, so the H5 mapping above is the whole story —
# there is nothing to switch between.

# ------------------------------------------------------- task readiness (S)
# The status a task carries in the Auto Planning System when the day is
# sequenced. Colours are the floor's own convention and must not be changed.
#
# Only four of these are simulated — see "Task readiness statuses" in README.md
# for where each one comes from and why two of them never fire here.
TASK_STATUS_COLORS = {
    'normal':          '#9bc2e6',   # 1 fabric relaxed 24h AND pattern in system
    'cut_queue':       '#833c0c',   # 2 queued by hand, not by the system
    'stretch':         '#ffd966',   # 3 last table of the batch, spreads the last yards
    'no_pattern':      '#a9d08e',   # 4 fabric relaxed, no pattern
    'no_fabric_time':  '#f4b084',   # 5 pattern in system, fabric not relaxed long enough
    'neither':         '#7030a0',   # 6 no pattern AND fabric not relaxed
    'no_fabric':       '#305496',   # 7 no fabric information at all
    'completed':       '#d9d9d9',   # 8 spreading and cutting finished
}

# Statuses the simulation does NOT produce, and why. Shown in the legend so the
# floor's full colour set is visible, but they will always read zero.
TASK_STATUS_NOT_SIMULATED = {
    'cut_queue': 'manual intervention — not a system arrangement, so not modelled',
    'no_fabric': 'Lot and Batch No are filled on every row, so this can never fire',
}

RELAX_HOURS = 24              # fabric must relax this long before it may be
                              # spread. This is a hard precondition, not a
                              # variable — a table is not released to the floor
                              # until its fabric has had its 24 hours. The
                              # simulation therefore treats every planned table
                              # as relaxed, and the two "not enough fabric"
                              # statuses stay in the legend reading zero.

# --------------------------------------------------------------- the machines
# F2 — 13 spreading machines grouped under 5 cutting machines.
CUT_GROUPS = {
    '24MC1': ['24-01', '24-02', '24-03'],
    '24MC2': ['24-04', '24-05'],
    '24MC3': ['24-06', '24-07'],
    '24MC4': ['24-08', '24-09', '24-10'],
    '24MC5': ['24-11', '24-12', '24-13'],
}

# F8 — two spreading machines can be served by a second cutting machine.
FLEXIBLE_CUT = {
    '24-03': ['24MC1', '24MC2'],
    '24-05': ['24MC2', '24MC3'],
}

# F5-F7 — night shift runs only these; everything else is day shift only.
NIGHT_SHIFT_SPREADERS = {'24-01', '24-02', '24-03'}
NIGHT_SHIFT_CUTTERS = {'24MC1'}

# ------------------------------------------------------------------ the shifts
# Every time in the model is minutes from the start of the day shift, so
# t = 0 is 07:15 and the Gantt reads in real clock time.
SHIFT_START_MINUTE = 7 * 60 + 15        # 07:15

# Day shift 07:15-20:00, all 13 spreaders and all 5 cutters.
# Night shift 18:00-05:00, only NIGHT_SHIFT_SPREADERS and NIGHT_SHIFT_CUTTERS.
# The two overlap 18:00-20:00 — that adds no capacity, it is the same machine
# running on, so a night-capable machine is simply available 07:15 -> 05:00.
DAY_SHIFT = (0, 765)                    # 07:15 - 20:00
NIGHT_SHIFT = (630, 1305)               # 17:45 - 05:00 (joins the day shift)

DAY_BREAKS = [(270, 330), (600, 630)]       # 11:45-12:45, 17:15-17:45
NIGHT_BREAKS = [(885, 915), (1125, 1155)]   # 22:00-22:30, 02:00-02:30

BREAKS_STOP_MACHINES = True   # spreading and cutting stop for breaks. Set False
                              # if relief staffing keeps the machines running —
                              # it is worth ~150 minutes a machine a day.

# ------------------------------------------------------ the spreading table
# G6 says a spreading machine blocks once two tables are sitting at its cutting
# end. That "two" is not a rule in itself — it is what a 21.2 m table gives you
# when the median marker is 8.8 yd. The model works in length, not in slots.
#
# A lay occupies its marker length on the table from the moment it is spread.
# Cutting then consumes that length PROGRESSIVELY between cut start and cut end
# — the lay is fed toward the cutting machine as it is cut — so space comes back
# gradually and the spreader can restart part way through the cut in front of
# it. Modelling it as a slot that frees only at cut_end overstates blocking by
# about two thirds.
SPREADING_TABLE_LENGTH_M = 21.2   # MEASURED. The usable length of one table.
YARDS_PER_METRE = 1.0936133
SPREADING_TABLE_LENGTH = SPREADING_TABLE_LENGTH_M * YARDS_PER_METRE

# Whether a new lay needs its full length free before it may start. True is
# conservative: in reality the spreader lays progressively and only needs the
# space to arrive as it goes.
LAY_NEEDS_FULL_LENGTH = True

# Fraction of a machine's staffed window that may be filled with spreading
# work when planning. The remainder absorbs blocking. Planning heuristic,
# not a written rule.
MACHINE_FILL_TARGET = 0.70

# ------------------------------------------------------------------ the times
# G2 — spreading and cutting time from layer count and marker length.
SPREAD_MIN_PER_LAYER_PER_YARD = 0.80 / 8.5
CUT_MIN_PER_LAYER_PER_YARD = 0.40 / 8.5

C_TABLE_EXTRA_MINUTES = 10   # G3 / I3 — a C table adds this to the B table
                             # on the same physical table. ESTIMATE.

# ------------------------------------------------------------------ the data
DATA_FILE = 'data/planppc.xlsx'
DATA_SHEET = 'HaveCut'

# J2 — only Type B tables enter the model; First Table = Y is excluded.
# J3 — non-universal markers (kids sizes, number sizes) still occupy machines
#      in the timeline but carry no compartment maths.
