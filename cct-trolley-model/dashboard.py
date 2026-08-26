# -*- coding: utf-8 -*-
"""
THE DASHBOARD
=============
Writes out/dashboard.html — a single self-contained page. Every slider
combination was already simulated by run.py, so moving a slider is a lookup,
not a re-run: the page responds instantly and needs no Python behind it.

Fleet size and cycle days are NOT looked up — they are arithmetic on
trolleys-per-day, computed live in the browser.
"""
import json

PALETTE = {
    # validated with the dataviz palette checker, light and dark separately
    'light': {'s1': '#3A6FB0', 's2': '#1E9E8A', 's3': '#E8A33D', 'bad': '#B23B32'},
    'dark':  {'s1': '#4A82C4', 's2': '#22A891', 's3': '#BB8228', 'bad': '#E0796E'},
}


def build_dashboard(payload: dict, trace: dict, path: str):
    data = json.dumps({
        'sweep': payload['sweep'],
        'assumptions': payload['assumptions'],
        'headline': {k: {'name': k,
                         'util': round(v['utilization_pct'], 2),
                         'tpd': round(v['trolleys_per_day'], 1),
                         'settings': v['settings']}
                     for k, v in payload['headline'].items()},
        'holdMinutes': payload['sweep_axes']['hold_minutes'],
        'maxBatches': payload['sweep_axes']['max_batches'],
        'planDates': payload['plan_dates'],
        'tables': payload['tables'],
        # ---- everything below is read by the Simulation tab only ----
        'cutGroups': payload['cut_groups'],
        'nightSpreaders': payload['night_shift_spreaders'],
        'spreaderShift': payload['spreader_shift'],
        'cutterShift': payload['cutter_shift'],
        'shiftEnd': payload['shift_end'],
        'dayShiftEnd': payload['day_shift_end'],
        'tableLengths': payload['table_lengths_m'],
        'statusColors': payload['status_colors'],
        'statusNotSimulated': payload['status_not_simulated'],
        'trace': trace,
    }, separators=(',', ':'), default=str)

    html = TEMPLATE.replace('/*__DATA__*/null', data)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trolley Utilization Simulation</title>
<style>
:root{
  --bg:#FBFCFD; --panel:#FFFFFF; --panel2:#EEF3F8; --ink:#101720; --muted:#5C6B7A;
  --rule:#DCE4ED; --rule2:#C3D0DE;
  --s1:#3A6FB0; --s2:#1E9E8A; --s3:#E8A33D; --bad:#B23B32;
  --badBg:#FBEDEB; --goodBg:#E9F6F3; --shadow:0 1px 3px rgba(16,23,32,.07);
}
:root[data-theme="dark"]{
  --bg:#0D1117; --panel:#161C24; --panel2:#1E2630; --ink:#E8EEF5; --muted:#93A2B2;
  --rule:#242D38; --rule2:#36434F;
  --s1:#4A82C4; --s2:#22A891; --s3:#BB8228; --bad:#E0796E;
  --badBg:#2A1512; --goodBg:#11251F; --shadow:none;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#0D1117; --panel:#161C24; --panel2:#1E2630; --ink:#E8EEF5; --muted:#93A2B2;
    --rule:#242D38; --rule2:#36434F;
    --s1:#4A82C4; --s2:#22A891; --s3:#BB8228; --bad:#E0796E;
    --badBg:#2A1512; --goodBg:#11251F; --shadow:none;
  }
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  background:var(--bg); color:var(--ink); padding:0 20px 64px;
  font:400 15px/1.55 "IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased;
}
.mono,.num{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums}
h1,h2,h3{margin:0;font-family:Archivo,"IBM Plex Sans",system-ui,sans-serif;
  letter-spacing:-.015em;text-wrap:balance}
h1{font-size:26px;font-weight:700}
h2{font-size:17px;font-weight:700}
h3{font-size:12px;font-weight:600}
.wrap{max-width:1600px;margin:0 auto}

/* ---------------------------------------------------------------- header */
header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;
  flex-wrap:wrap;padding:26px 0 18px;border-bottom:1px solid var(--rule)}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.15em;
  text-transform:uppercase;color:var(--muted);margin-bottom:6px}
button.theme{background:var(--panel);color:var(--muted);border:1px solid var(--rule2);
  border-radius:4px;padding:7px 12px;font-size:12px;cursor:pointer;font-family:inherit}
button.theme:hover{color:var(--ink);border-color:var(--muted)}

/* ------------------------------------------------------------------ grid */
/* minmax(0,1fr), not 1fr: a grid item defaults to min-width:auto, so a wide
   chart would stretch the column and push the whole page sideways instead of
   scrolling inside its own panel. */
.cols{display:grid;grid-template-columns:290px minmax(0,1fr);gap:24px;margin-top:24px;
  align-items:start}
@media (max-width:940px){.cols{grid-template-columns:minmax(0,1fr)}}
.cols>*{min-width:0}
.panel,details.panel{min-width:0}
/* The verdict charts are drawn at 700 wide; on a wide page let them breathe a
   little but never balloon. */
#fleetChart svg,#ladder svg{max-width:820px}

/* -------------------------------------------------------------- controls */
.rail{position:sticky;top:16px;display:flex;flex-direction:column;gap:14px}
@media (max-width:940px){.rail{position:static}}
.ctl{background:var(--panel);border:1px solid var(--rule);border-radius:6px;
  padding:15px 16px;box-shadow:var(--shadow)}
.ctl h3{color:var(--muted);text-transform:uppercase;letter-spacing:.09em;
  font-family:"IBM Plex Mono",monospace;font-size:10px;font-weight:400;margin-bottom:12px}
.field{margin-bottom:17px}
.field:last-child{margin-bottom:0}
.field>label{display:flex;justify-content:space-between;align-items:baseline;
  gap:8px;font-size:13px;font-weight:500;margin-bottom:7px}
.field .val{font-family:"IBM Plex Mono",monospace;font-size:12.5px;color:var(--s1);font-weight:500}
.hint{font-size:11.5px;color:var(--muted);line-height:1.45;margin-top:6px}
.chg{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:9.5px;
  letter-spacing:.06em;border:1px solid var(--rule2);border-radius:3px;
  padding:1px 5px;color:var(--muted);margin-right:6px;vertical-align:1px}

input[type=range]{width:100%;-webkit-appearance:none;appearance:none;background:transparent;
  margin:2px 0;cursor:pointer}
input[type=range]::-webkit-slider-runnable-track{height:4px;border-radius:2px;background:var(--rule2)}
input[type=range]::-moz-range-track{height:4px;border-radius:2px;background:var(--rule2)}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;
  border-radius:50%;background:var(--s1);border:2px solid var(--panel);margin-top:-6px;
  box-shadow:0 0 0 1px var(--rule2)}
input[type=range]::-moz-range-thumb{width:16px;height:16px;border-radius:50%;
  background:var(--s1);border:2px solid var(--panel);box-shadow:0 0 0 1px var(--rule2)}
input[type=range]:focus-visible{outline:2px solid var(--s1);outline-offset:4px;border-radius:3px}

.seg{display:flex;gap:0;border:1px solid var(--rule2);border-radius:5px;overflow:hidden}
.seg button{flex:1;background:var(--panel);border:0;border-right:1px solid var(--rule2);
  padding:7px 4px;font:500 12.5px/1 "IBM Plex Sans",sans-serif;color:var(--muted);cursor:pointer}
.seg button:last-child{border-right:0}
.seg button[aria-pressed=true]{background:var(--s1);color:#fff}
.seg button:focus-visible{outline:2px solid var(--s1);outline-offset:-2px}

.presets{display:flex;gap:8px}
.presets button{flex:1;background:var(--panel2);border:1px solid var(--rule2);border-radius:5px;
  padding:8px 6px;font:500 12px/1.3 "IBM Plex Sans",sans-serif;color:var(--ink);cursor:pointer}
.presets button:hover{border-color:var(--s1);color:var(--s1)}

.warn{margin-top:10px;background:var(--badBg);border:1px solid var(--bad);border-radius:4px;
  padding:9px 11px;font-size:11.5px;color:var(--ink);line-height:1.45}
.warn strong{color:var(--bad)}

/* --------------------------------------------------------------- verdict */
.verdict{border-radius:7px;border:1px solid var(--rule);background:var(--panel);
  padding:22px 24px;box-shadow:var(--shadow);
  display:grid;grid-template-columns:1fr auto;gap:24px;align-items:center}
@media (max-width:640px){.verdict{grid-template-columns:1fr}}
.verdict.short{border-color:var(--bad);background:var(--badBg)}
.verdict.ok{border-color:var(--s2);background:var(--goodBg)}
.vlabel{font-family:Archivo,sans-serif;font-weight:700;font-size:12px;letter-spacing:.11em;
  text-transform:uppercase}
.verdict.short .vlabel{color:var(--bad)}
.verdict.ok .vlabel{color:var(--s2)}
.vbig{font-family:Archivo,sans-serif;font-weight:700;font-size:40px;line-height:1.05;
  margin:9px 0 0;letter-spacing:-.025em}
.vsub{font-size:13.5px;color:var(--muted);margin-top:8px;max-width:52ch}
.vsub b{color:var(--ink)}

/* --------------------------------------------------------------- tiles */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:12px;margin-top:16px}
.tile{background:var(--panel);border:1px solid var(--rule);border-radius:6px;
  padding:14px 15px;box-shadow:var(--shadow)}
.tile .k{font-family:"IBM Plex Mono",monospace;font-size:9.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);line-height:1.4;min-height:27px}
.tile .v{font-family:Archivo,sans-serif;font-weight:700;font-size:26px;margin:8px 0 0;
  letter-spacing:-.02em}
.tile .v em{font-style:normal;font-size:15px;color:var(--muted);font-weight:600}
.tile .d{font-family:"IBM Plex Mono",monospace;font-size:11.5px;margin-top:5px;color:var(--muted)}
.tile .d.up{color:var(--s2)} .tile .d.down{color:var(--bad)}

/* --------------------------------------------------------------- panels */
.panel{background:var(--panel);border:1px solid var(--rule);border-radius:6px;
  padding:18px 20px;box-shadow:var(--shadow);margin-top:16px}
.panel>h2{margin-bottom:3px}
.panel>.sub{font-size:12.5px;color:var(--muted);margin:0 0 15px;max-width:70ch}
.split{display:grid;grid-template-columns:190px 1fr;gap:26px;align-items:center}
@media (max-width:700px){.split{grid-template-columns:1fr}}
svg{display:block;max-width:100%;height:auto}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;font-size:12px;color:var(--muted)}
.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;
  vertical-align:0px}
footer{margin-top:34px;padding-top:18px;border-top:1px solid var(--rule);
  font-size:12px;color:var(--muted);line-height:1.6}
footer code{font-family:"IBM Plex Mono",monospace;font-size:11.5px;
  background:var(--panel2);padding:1px 5px;border-radius:3px}
@media (prefers-reduced-motion:no-preference){
  .barfill,.compfill,.vbig,.tile .v{transition:all .22s cubic-bezier(.4,0,.2,1)}
}

/* ------------------------------------------------------------------ tabs */
.tabs{display:flex;gap:2px;margin-top:-1px;border-bottom:1px solid var(--rule)}
.tab{background:none;border:0;border-bottom:2px solid transparent;padding:11px 2px;
  margin-right:22px;font:600 13.5px/1 Archivo,"IBM Plex Sans",sans-serif;
  color:var(--muted);cursor:pointer;letter-spacing:-.01em}
.tab:hover{color:var(--ink)}
.tab[aria-selected=true]{color:var(--s1);border-bottom-color:var(--s1)}
.tab:focus-visible{outline:2px solid var(--s1);outline-offset:2px;border-radius:2px}

/* ------------------------------------------------------- simulation tab */
.scrollx{overflow-x:auto;overflow-y:hidden}
.calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}
.calendar .dow{font-family:"IBM Plex Mono",monospace;font-size:9px;color:var(--muted);
  text-align:center;padding-bottom:3px;letter-spacing:.04em}
.calendar button{aspect-ratio:1;background:var(--panel2);border:1px solid var(--rule2);
  border-radius:4px;font:500 11.5px/1 "IBM Plex Mono",monospace;color:var(--ink);cursor:pointer;
  display:flex;align-items:center;justify-content:center;padding:0}
.calendar button:hover{border-color:var(--s1);color:var(--s1)}
.calendar button[aria-pressed=true]{background:var(--s1);border-color:var(--s1);color:#fff}
.calendar button:focus-visible{outline:2px solid var(--s1);outline-offset:1px}
.calendar span{aspect-ratio:1;display:flex;align-items:center;justify-content:center;
  font:400 11.5px/1 "IBM Plex Mono",monospace;color:var(--rule2)}
.calmonth{font-family:"IBM Plex Mono",monospace;font-size:10.5px;color:var(--muted);
  letter-spacing:.08em;text-transform:uppercase;margin:2px 0 8px}

/* The cursor rides the chart's own axis: same width, same left gutter, inside
   the same scroller, so the handle sits over the hour it selects. */
.cursorhead{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  margin-bottom:6px}
.cursorhead label{font-size:12px;color:var(--muted)}
.cursorhead .num{font-size:12.5px;font-weight:600}
/* The chart fills the panel, and only scrolls once the panel is narrower than
   the chart can usefully be drawn. The gutters are fixed pixels and match the
   SVG's own L and R, so the slider handle sits over the hour it selects at any
   width. */
.ganttinner{min-width:1120px}
.cursorrow{padding:0 14px 2px 96px;box-sizing:border-box}
.cursorrow input[type=range]{width:100%;margin:0;display:block}

.swatches{display:flex;flex-wrap:wrap;gap:5px 16px;margin-top:13px;font-size:11.5px;
  color:var(--muted);line-height:1.35}
.swatches span{display:flex;align-items:center;gap:6px}
.swatches i{width:11px;height:11px;border-radius:2px;flex:none;
  border:1px solid rgba(128,128,128,.55)}
.swatches b{color:var(--ink);font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:600}
.swatches .off{opacity:.45}

.parity{display:inline-flex;align-items:center;gap:8px;border-radius:4px;padding:6px 11px;
  font-size:12px;margin-bottom:14px;border:1px solid var(--rule2);background:var(--panel2)}
.parity.ok{border-color:var(--s2);background:var(--goodBg)}
.parity.bad{border-color:var(--bad);background:var(--badBg)}
.parity .num{font-weight:600}

details.panel>summary{cursor:pointer;list-style:none;display:flex;align-items:baseline;
  gap:12px;flex-wrap:wrap}
details.panel>summary::-webkit-details-marker{display:none}
details.panel>summary::before{content:"\25B8";color:var(--muted);font-size:12px;
  transition:transform .15s}
details.panel[open]>summary::before{transform:rotate(90deg)}
details.panel>summary:focus-visible{outline:2px solid var(--s1);outline-offset:3px;border-radius:3px}
details.panel>summary h2{display:inline}
details.panel>summary .sum{font-family:"IBM Plex Mono",monospace;font-size:11.5px;
  color:var(--muted);margin-left:auto}
details.panel>.sub{margin-top:12px}
h3.sechead{font-size:12px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.09em;font-family:"IBM Plex Mono",monospace;font-weight:400;
  margin:22px 0 10px}

.trolleyrow{display:flex;flex-wrap:wrap;gap:10px}
.tcard{border:1px solid var(--rule2);border-radius:5px;padding:8px;background:var(--panel2);width:112px}
.tcard .h{font-family:"IBM Plex Mono",monospace;font-size:9.5px;color:var(--muted);
  display:flex;justify-content:space-between;margin-bottom:6px}
.tcard .c{height:19px;border-radius:2px;margin-bottom:3px;display:flex;align-items:center;
  justify-content:space-between;padding:0 5px;font-family:"IBM Plex Mono",monospace;
  font-size:9.5px;color:#101720}
.tcard .c.empty{background:transparent;border:1px dashed var(--rule2)}
.filmhead{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);
  margin:16px 0 8px;letter-spacing:.05em}
.filmhead:first-child{margin-top:0}

table.tasks{border-collapse:collapse;width:100%;font-size:12px}
table.tasks th{text-align:left;font-family:"IBM Plex Mono",monospace;font-size:9.5px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:400;
  padding:0 10px 7px 0;border-bottom:1px solid var(--rule2);white-space:nowrap;
  cursor:pointer;user-select:none}
table.tasks th:hover{color:var(--ink)}
table.tasks td{padding:6px 10px 6px 0;border-bottom:1px solid var(--rule);white-space:nowrap}
table.tasks td.n{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;
  text-align:right;padding-right:16px}
table.tasks tr:hover td{background:var(--panel2)}
table.tasks .dot{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:7px;
  vertical-align:-1px;border:1px solid rgba(128,128,128,.55)}
.muted{color:var(--muted)}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div>
    <div class="eyebrow">Central Cutting &middot; Job Sequence &amp; Panel Loading</div>
    <h1>Trolley Utilization Simulation</h1>
  </div>
  <button class="theme" id="themeBtn" type="button">Dark mode</button>
</header>

<div class="tabs" role="tablist" aria-label="Views">
  <button class="tab" type="button" role="tab" id="tabBtnUtil"
          aria-controls="tabUtil" aria-selected="true">Utilization</button>
  <button class="tab" type="button" role="tab" id="tabBtnSim"
          aria-controls="tabSim" aria-selected="false" tabindex="-1">Simulation</button>
</div>

<section id="tabUtil" role="tabpanel" aria-labelledby="tabBtnUtil">
<div class="cols">

  <!-- ============================ CONTROLS ============================ -->
  <div class="rail">
    <div class="ctl">
      <h3>Start from</h3>
      <div class="presets">
        <button type="button" data-preset="today">Today</button>
        <button type="button" data-preset="proposal">The proposal</button>
      </div>
    </div>

    <div class="ctl">
      <h3>The three changes</h3>

      <div class="field">
        <label for="mo"><span><span class="chg">1</span>Same-MO sequencing</span>
          <span class="val" id="moVal">off</span></label>
        <div class="seg" role="group" aria-label="Same-MO sequencing">
          <button type="button" data-mo="0" aria-pressed="true">Off</button>
          <button type="button" data-mo="1" aria-pressed="false">On</button>
        </div>
        <div class="hint">Put tables of the same MO back-to-back at one workstation,
          same batch first, then different batches.</div>
      </div>

      <div class="field">
        <label for="batches"><span><span class="chg">2</span>Batches per trolley</span>
          <span class="val" id="batchVal">1</span></label>
        <div class="seg" role="group" aria-label="Max batches per trolley">
          <button type="button" data-batch="1" aria-pressed="true">1</button>
          <button type="button" data-batch="2" aria-pressed="false">2</button>
          <button type="button" data-batch="3" aria-pressed="false">3</button>
        </div>
        <div class="hint">Separate compartments, same MO and colour. 1 = today's rule.</div>
        <div class="warn" id="batchWarn" hidden>
          <strong>3 is not allowed on the floor.</strong> A trolley may carry at most
          two fabric batches. Shown for comparison only.</div>
      </div>

      <div class="field">
        <label for="hold"><span><span class="chg">3</span>WIP hold</span>
          <span class="val" id="holdVal">off</span></label>
        <input type="range" id="hold" min="0" max="6" step="1" value="0"
               aria-label="WIP hold minutes">
        <div class="hint">How long a part-filled trolley waits in CCT WIP for a later
          table of the same MO, colour and film size.</div>
      </div>

      <div class="field" id="wsField">
        <label><span>It comes back to</span><span class="val" id="wsVal">any workstation</span></label>
        <div class="seg" role="group" aria-label="Which workstation the trolley returns to">
          <button type="button" data-ws="0" aria-pressed="false">Same only</button>
          <button type="button" data-ws="1" aria-pressed="true">Any</button>
        </div>
        <div class="hint">Whether a parked trolley may travel to a different
          workstation. Nobody has costed how it physically gets there.</div>
      </div>
    </div>

    <div class="ctl">
      <h3>The fleet</h3>
      <div class="field">
        <label for="cycle"><span>Trolley round trip</span>
          <span class="val" id="cycleVal">7 days</span></label>
        <input type="range" id="cycle" min="3" max="10" step="0.5" value="7"
               aria-label="Cycle days">
        <div class="hint">5 days is the lead-time allowance. ~7 is the estimate of
          what really happens — and it has never been measured.</div>
      </div>
      <div class="field">
        <label for="fleet"><span>Trolleys owned</span>
          <span class="val" id="fleetVal">1,200</span></label>
        <input type="range" id="fleet" min="600" max="2200" step="50" value="1200"
               aria-label="Fleet size">
      </div>
    </div>
  </div>

  <!-- ============================= OUTPUT ============================= -->
  <div>
    <div class="verdict" id="verdict">
      <div>
        <div class="vlabel" id="vlabel">—</div>
        <div class="vbig" id="vbig">—</div>
        <div class="vsub" id="vsub"></div>
      </div>
      <div id="fleetDial"></div>
    </div>

    <div class="tiles">
      <div class="tile"><div class="k">Trolley utilization</div>
        <div class="v" id="tUtil">—</div><div class="d" id="dUtil"></div></div>
      <div class="tile"><div class="k">Trolleys out per day</div>
        <div class="v" id="tTpd">—</div><div class="d" id="dTpd"></div></div>
      <div class="tile"><div class="k">Garments per trolley</div>
        <div class="v" id="tPpt">—</div><div class="d" id="dPpt"></div></div>
      <div class="tile"><div class="k">Cycle the fleet covers</div>
        <div class="v" id="tCycle">—</div><div class="d" id="dCycle"></div></div>
      <div class="tile"><div class="k">Avg wait in WIP</div>
        <div class="v" id="tWait">—</div><div class="d" id="dWait"></div></div>
    </div>

    <div class="panel">
      <h2>What one trolley looks like</h2>
      <p class="sub">Utilization is compartments used &divide; 5. This is that number
        drawn as the trolley it describes — filled compartments at the bottom,
        empty space travelling for free at the top.</p>
      <div class="split">
        <div id="trolley"></div>
        <div>
          <div id="trolleyText" style="font-size:14px;line-height:1.65"></div>
          <div class="legend">
            <span><i style="background:var(--s2)"></i>Loaded</span>
            <span><i style="background:var(--rule2)"></i>Empty — travelling for nothing</span>
          </div>
        </div>
      </div>
    </div>

    <div class="panel">
      <h2>Fleet needed against fleet owned</h2>
      <p class="sub">A trolley dispatched today is gone for the whole round trip, so
        the fleet has to cover that many days of dispatches at once.</p>
      <div id="fleetChart"></div>
    </div>

    <div class="panel">
      <h2>Where these settings sit</h2>
      <p class="sub">The four approval steps, each one the previous plus a single
        change. Your current settings are marked if they match one.</p>
      <div id="ladder"></div>
    </div>

    <footer id="footer"></footer>
  </div>
</div>
</section>

<!-- =========================== SIMULATION =========================== -->
<section id="tabSim" role="tabpanel" aria-labelledby="tabBtnSim" hidden>
<div class="cols">

  <div class="rail">
    <div class="ctl">
      <h3>Plan date</h3>
      <div class="calmonth" id="calMonth"></div>
      <div class="calendar" id="calendar"></div>
      <div class="hint" id="dayMeta"></div>
    </div>

    <div class="ctl">
      <h3>The three changes</h3>

      <div class="field">
        <label><span><span class="chg">1</span>Same-MO sequencing</span>
          <span class="val" id="seqVal">off</span></label>
        <div class="seg" role="group" aria-label="Same-MO sequencing">
          <button type="button" data-seq="today" aria-pressed="true">Off</button>
          <button type="button" data-seq="mo_aware" aria-pressed="false">On</button>
        </div>
        <div class="hint">Off scatters a batch across the three machines of a cut
          group. On pairs tables first and keeps each pair on one machine,
          back-to-back &mdash; watch the brackets appear.</div>
      </div>

      <div class="field">
        <label><span><span class="chg">2</span>Batches per trolley</span>
          <span class="val" id="simBatchVal">1</span></label>
        <div class="seg" role="group" aria-label="Max batches per trolley">
          <button type="button" data-simbatch="1" aria-pressed="true">1</button>
          <button type="button" data-simbatch="2" aria-pressed="false">2</button>
          <button type="button" data-simbatch="3" aria-pressed="false">3</button>
        </div>
        <div class="hint">Separate compartments, same MO and colour. 1 = today's rule.</div>
      </div>

      <div class="field">
        <label for="simHold"><span><span class="chg">3</span>WIP hold</span>
          <span class="val" id="simHoldVal">off</span></label>
        <input type="range" id="simHold" min="0" max="6" step="1" value="0"
               aria-label="WIP hold minutes">
        <div class="hint">How long a part-filled trolley waits for a later table of
          the same MO, colour and film size.</div>
      </div>

      <div class="field" id="simWsField">
        <label><span>It comes back to</span>
          <span class="val" id="simWsVal">any workstation</span></label>
        <div class="seg" role="group" aria-label="Which workstation the trolley returns to">
          <button type="button" data-simws="0" aria-pressed="false">Same only</button>
          <button type="button" data-simws="1" aria-pressed="true">Any</button>
        </div>
      </div>
    </div>

    <div class="ctl">
      <h3>Idle time</h3>
      <div class="field">
        <label><span>Spreading table length</span>
          <span class="val" id="bufVal"></span></label>
        <div class="seg" id="tableSeg" role="group" aria-label="Spreading table length"></div>
        <div class="hint">Rule G6 &mdash; the spreader stops when there is not enough
          table free for the next lay. The lay in front gives its length back
          gradually as the cutter eats it, so this is the hatching on the chart.
          See <code>IDLE_TIME.md</code>.</div>
      </div>
    </div>
  </div>

  <div>
    <div class="panel">
      <h2>1 &middot; Job Sequence &mdash; <span id="ganttDate"></span></h2>
      <p class="sub">Every table of the day placed on a spreading machine, with its
        estimated spreading time, and the cutting that follows it on the cut machine
        serving that group. Colour is the task's readiness when the day was planned.</p>
      <div class="cursorhead">
        <label for="cursor">Actually finished spreading by</label>
        <span class="num" id="cursorVal"></span>
      </div>
      <div class="scrollx">
        <div class="ganttinner">
          <div class="cursorrow">
            <input type="range" id="cursor" min="0" max="1" step="1" value="0"
                   aria-label="Time cursor along the chart's own timeline">
          </div>
          <div id="gantt"></div>
        </div>
      </div>
      <div class="swatches" id="statusLegend"></div>
      <div class="hint" id="idleNote"></div>
      <div class="hint" id="slipNote"></div>
    </div>

    <details class="panel" id="taskPanel">
      <summary>
        <h2>Tasks prepared for <span id="listDate"></span></h2>
        <span class="sum" id="taskSummary"></span>
      </summary>
      <p class="sub">The day as the planner receives it. Click a column to sort.</p>
      <div class="scrollx"><table class="tasks" id="taskTable"></table></div>
      <div class="hint" id="taskNote"></div>
    </details>

    <details class="panel" id="loadPanel">
      <summary>
        <h2>2 &middot; Panel Loading &mdash; onto trolleys at the end of cutting</h2>
        <span class="sum" id="loadSummary"></span>
      </summary>
      <p class="sub">The same day's cut panels, loaded compartment by compartment.
        A compartment holds one size of one batch, up to 150 pieces (H1); a trolley
        holds five compartments of one film width only (H3, H4).</p>
      <div id="parity" class="parity"></div>
      <div class="scrollx"><table class="tasks" id="trolleyTable"></table></div>
      <h3 class="sechead">Every trolley of the day</h3>
      <div id="trolleys"></div>
    </details>
  </div>
</div>
</section>

</div>

<script>
const DATA = /*__DATA__*/null;
const A = DATA.assumptions;
const HOLDS = DATA.holdMinutes;

const state = {
  mo: 0, batches: 1, holdIdx: 0, anyWs: 1,
  cycle: A.cycle_days_estimated, fleet: A.fleet_size,
};

const PRESETS = {
  today:    {mo:0, batches:1, holdIdx:0, anyWs:1},
  proposal: {mo:1, batches:2, holdIdx:HOLDS.indexOf(A.wip_hold_minutes), anyWs:A.wip_hold_any_workstation?1:0},
};

const $ = id => document.getElementById(id);
const fmt = (n,d=0) => n.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});

function key(mo, batches, hold, anyWs){
  if (hold === 0) anyWs = 1;
  return `${mo}|${batches}|${hold}|${anyWs}`;
}
function lookup(s){
  return DATA.sweep[key(s.mo, s.batches, HOLDS[s.holdIdx], s.anyWs)];
}
const BASELINE = DATA.sweep[key(0,1,0,1)];

/* ---------------------------------------------------------------- visuals */
function trolleySvg(util){
  // 5 compartments, filled from the bottom, in proportion to utilization
  const used = util/100*5, W=170, H=210, x=26, w=118, top=16, ch=32, gap=4;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Trolley with ${(util/100*5).toFixed(2)} of 5 compartments loaded">`;
  s += `<rect x="${x-8}" y="${top-8}" width="${w+16}" height="${5*(ch+gap)+12}" rx="5"
         fill="none" stroke="var(--rule2)" stroke-width="2"/>`;
  for (let i=0;i<5;i++){
    const slot = 4-i;                                   // fill bottom-up
    const y = top + slot*(ch+gap);
    const f = Math.max(0, Math.min(1, used - i));
    s += `<rect x="${x}" y="${y}" width="${w}" height="${ch}" rx="2"
           fill="var(--panel2)" stroke="var(--rule2)" stroke-width="1"/>`;
    if (f > 0.004){
      s += `<rect class="compfill" x="${x+2}" y="${y+2}" width="${(w-4)*f}" height="${ch-4}"
             rx="1.5" fill="var(--s2)"/>`;
    }
  }
  const by = top + 5*(ch+gap) + 8;
  s += `<rect x="${x-8}" y="${by}" width="${w+16}" height="4" rx="2" fill="var(--rule2)"/>`;
  s += `<circle cx="${x+6}" cy="${by+12}" r="6" fill="none" stroke="var(--rule2)" stroke-width="2"/>`;
  s += `<circle cx="${x+w-6}" cy="${by+12}" r="6" fill="none" stroke="var(--rule2)" stroke-width="2"/>`;
  return s + '</svg>';
}

function fleetDial(required, fleet){
  const r=52, c=2*Math.PI*r, pct=Math.min(1.35, required/fleet);
  const over = required > fleet;
  const col = over ? 'var(--bad)' : 'var(--s2)';
  return `<svg viewBox="0 0 130 130" width="126" height="126" role="img"
    aria-label="${fmt(required)} trolleys needed against ${fmt(fleet)} owned">
    <circle cx="65" cy="65" r="${r}" fill="none" stroke="var(--rule2)" stroke-width="11"/>
    <circle cx="65" cy="65" r="${r}" fill="none" stroke="${col}" stroke-width="11"
      stroke-linecap="butt" stroke-dasharray="${Math.min(pct,1)*c} ${c}"
      transform="rotate(-90 65 65)"/>
    <text x="65" y="60" text-anchor="middle" class="num" font-size="21" font-weight="700"
      fill="var(--ink)">${Math.round(required/fleet*100)}%</text>
    <text x="65" y="77" text-anchor="middle" font-size="10" fill="var(--muted)">of fleet</text>
  </svg>`;
}

function fleetChart(tpd, baseTpd, cycle, fleet){
  const mine = tpd*cycle, base = baseTpd*cycle;
  const col = mine > fleet ? 'bad' : 's2';
  // When the sliders sit on today's rules the two bars are the same number —
  // draw one row rather than two identical ones.
  const rows = Math.abs(mine - base) < 1
    ? [['Today — these settings', mine, col]]
    : [['Today', base, 's1'], ['These settings', mine, col]];
  const W=700, L=150, R=68, rowH=52, H=rows.length*rowH+30;
  const vmax = Math.max(fleet, ...rows.map(r=>r[1]))*1.1;
  const x = v => L + (W-L-R)*v/vmax;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Trolleys required versus fleet owned">`;
  rows.forEach((row,i)=>{
    const y = 14+i*rowH;
    s += `<text x="0" y="${y+18}" font-size="12.5" font-weight="500" fill="var(--ink)">${row[0]}</text>`;
    s += `<text x="0" y="${y+33}" font-size="10.5" class="num" fill="var(--muted)">${fmt(row[1]/cycle,0)}/day &#215; ${cycle}d</text>`;
    s += `<rect x="${L}" y="${y}" width="${W-L-R}" height="24" rx="3" fill="var(--panel2)" stroke="var(--rule2)"/>`;
    s += `<rect class="barfill" x="${L}" y="${y}" width="${Math.max(0,x(row[1])-L)}" height="24" rx="3" fill="var(--${row[2]})"/>`;
    s += `<text x="${x(row[1])+8}" y="${y+17}" class="num" font-size="13" font-weight="600" fill="var(--ink)">${fmt(row[1])}</text>`;
  });
  s += `<line x1="${x(fleet)}" x2="${x(fleet)}" y1="4" y2="${H-22}" stroke="var(--ink)"
         stroke-width="1.5" stroke-dasharray="4 3" opacity=".5"/>`;
  s += `<text x="${x(fleet)}" y="${H-8}" text-anchor="middle" class="num" font-size="10.5"
         fill="var(--ink)" opacity=".75">owned: ${fmt(fleet)}</text>`;
  return s+'</svg>';
}
const over = (a,b)=>a>b;

function ladder(cur){
  const steps = Object.values(DATA.headline);
  const W=700, BX=214, VW=68, H=steps.length*46+8;
  const bw = W - BX - VW;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Utilization by approval step">`;
  steps.forEach((st,i)=>{
    const y = i*46+6;
    const isCur = st.settings.mo_aware_sequencing===!!cur.mo
      && st.settings.max_batches===cur.batches
      && st.settings.wip_hold_minutes===HOLDS[cur.holdIdx]
      && (HOLDS[cur.holdIdx]===0 || st.settings.hold_any_workstation===!!cur.anyWs);
    const col = isCur ? 'var(--s3)' : 'var(--s1)';
    s += `<text x="0" y="${y+18}" font-size="12.5" font-weight="${isCur?600:400}"
           fill="var(--ink)">${st.name.replace(/^S\d+\s+/,'')}</text>`;
    // "you are here" lives in the label column, where it can never be clipped
    s += `<text x="0" y="${y+32}" font-size="10" class="num"
           fill="${isCur?'var(--s3)':'var(--muted)'}" font-weight="${isCur?600:400}">`
       + `${st.name.split(' ')[0]}${isCur?' &#183; you are here':''}</text>`;
    s += `<rect x="${BX}" y="${y+2}" width="${bw}" height="22" rx="3"
           fill="var(--panel2)" stroke="var(--rule2)"/>`;
    s += `<rect x="${BX}" y="${y+2}" width="${bw*st.util/100}" height="22" rx="3" fill="${col}"/>`;
    // direct label on every bar — required relief for the amber's contrast
    s += `<text x="${BX+bw+8}" y="${y+18}" class="num" font-size="12.5"
           font-weight="600" fill="var(--ink)">${st.util.toFixed(1)}%</text>`;
  });
  return s+'</svg>';
}

/* ------------------------------------------------------------------ render */
function render(){
  const r = lookup(state);
  const cycle = state.cycle, fleet = state.fleet;
  const required = r.trolleys_per_day * cycle;
  const spare = fleet - required;
  const short = spare < 0;

  // verdict
  const v = $('verdict');
  v.className = 'verdict ' + (short ? 'short' : 'ok');
  $('vlabel').textContent = short ? 'The fleet does not cover this' : 'The fleet covers this';
  $('vbig').textContent = fmt(required) + ' trolleys needed';
  $('vsub').innerHTML = short
    ? `At <b>${fmt(r.trolleys_per_day,0)} trolleys a day</b> and a <b>${cycle}-day</b> round trip,
       Central Cutting needs ${fmt(required)} trolleys in circulation. You own
       ${fmt(fleet)} — <b>${fmt(-spare)} short</b>.`
    : `At <b>${fmt(r.trolleys_per_day,0)} trolleys a day</b> and a <b>${cycle}-day</b> round trip,
       ${fmt(required)} trolleys stay in circulation — <b>${fmt(spare)} spare</b> inside the
       ${fmt(fleet)} you own.`;
  $('fleetDial').innerHTML = fleetDial(required, fleet);

  // tiles
  const d = (now, was, better, unit='', dec=1) => {
    const diff = now - was;
    if (Math.abs(diff) < 0.05) return ['vs today: no change',''];
    const good = better === 'up' ? diff > 0 : diff < 0;
    return [`vs today: ${diff>0?'+':''}${fmt(diff,dec)}${unit}`, good?'up':'down'];
  };
  const set = (tid, did, val, tuple) => {
    $(tid).innerHTML = val;
    $(did).textContent = tuple[0];
    $(did).className = 'd ' + tuple[1];
  };
  set('tUtil','dUtil', r.utilization_pct.toFixed(1)+'<em>%</em>',
      d(r.utilization_pct, BASELINE.utilization_pct, 'up', ' pt'));
  set('tTpd','dTpd', fmt(r.trolleys_per_day,0),
      d(r.trolleys_per_day, BASELINE.trolleys_per_day, 'down', '', 0));
  set('tPpt','dPpt', fmt(r.pieces_per_trolley,0),
      d(r.pieces_per_trolley, BASELINE.pieces_per_trolley, 'up', '', 0));
  const cyc = fleet / r.trolleys_per_day, baseCyc = fleet / BASELINE.trolleys_per_day;
  set('tCycle','dCycle', cyc.toFixed(1)+'<em> days</em>',
      d(cyc, baseCyc, 'up', ' d'));
  set('tWait','dWait',
      r.avg_wait_hours > 0 ? r.avg_wait_hours.toFixed(1)+'<em> h</em>' : '<em>none</em>',
      ['trolleys are not held', '']);
  if (r.avg_wait_hours > 0){
    $('dWait').textContent = `${fmt(HOLDS[state.holdIdx])} min allowed`;
  }

  // trolley
  $('trolley').innerHTML = trolleySvg(r.utilization_pct);
  const usedComp = r.utilization_pct/100*5;
  $('trolleyText').innerHTML =
    `<b>${usedComp.toFixed(2)} of 5 compartments</b> carry panels, on average, on every
     trolley that leaves Central Cutting.<br><br>
     That is <b>${fmt(r.pieces_per_trolley,0)} garments</b> per trolley against a
     ${fmt(A.trolley_compartments*A.compartment_cap)} ceiling. The remaining
     <b>${(5-usedComp).toFixed(2)} compartments</b> travel the full
     ${cycle}-day round trip empty.`;

  $('fleetChart').innerHTML = fleetChart(r.trolleys_per_day, BASELINE.trolleys_per_day, cycle, fleet);
  $('ladder').innerHTML = ladder(state);

  // control labels
  $('moVal').textContent = state.mo ? 'on' : 'off';
  $('batchVal').textContent = state.batches;
  $('holdVal').textContent = HOLDS[state.holdIdx] === 0 ? 'off' : HOLDS[state.holdIdx] + ' min';
  $('wsVal').textContent = state.anyWs ? 'any workstation' : 'same only';
  $('cycleVal').textContent = cycle + ' days';
  $('fleetVal').textContent = fmt(fleet);
  $('batchWarn').hidden = state.batches !== 3;
  $('wsField').style.opacity = HOLDS[state.holdIdx] === 0 ? .4 : 1;
  $('wsField').querySelectorAll('button').forEach(b => b.disabled = HOLDS[state.holdIdx] === 0);

  document.querySelectorAll('[data-mo]').forEach(b =>
    b.setAttribute('aria-pressed', String(+b.dataset.mo === state.mo)));
  document.querySelectorAll('[data-batch]').forEach(b =>
    b.setAttribute('aria-pressed', String(+b.dataset.batch === state.batches)));
  document.querySelectorAll('[data-ws]').forEach(b =>
    b.setAttribute('aria-pressed', String(+b.dataset.ws === state.anyWs)));

  $('footer').innerHTML =
    `${DATA.planDates} plan dates &middot; ${fmt(DATA.tables)} tables &middot;
     ${fmt(DATA.tables/DATA.planDates,0)} a day. Trolley utilization is compartments
     used &divide; ${A.trolley_compartments} (rule H6), pooled across all days.
     A trolley may carry at most ${A.max_batches_per_trolley} fabric batches, and no
     more than ${A.trolley_bays} may be parked and waiting at once (rule H7).
     The ${A.cycle_days_estimated}-day round trip is an <b>estimate, not a measurement</b> —
     it is the number this whole page is most sensitive to.<br><br>
     Every value here comes from <code>assumptions.py</code>. Change one, re-run
     <code>python run.py</code>, and this page updates.`;
}

/* ------------------------------------------------------------------ wiring */
$('hold').addEventListener('input', e => { state.holdIdx = +e.target.value; render(); });
$('cycle').addEventListener('input', e => { state.cycle = +e.target.value; render(); });
$('fleet').addEventListener('input', e => { state.fleet = +e.target.value; render(); });

document.querySelectorAll('[data-mo]').forEach(b =>
  b.addEventListener('click', () => { state.mo = +b.dataset.mo; render(); }));
document.querySelectorAll('[data-batch]').forEach(b =>
  b.addEventListener('click', () => { state.batches = +b.dataset.batch; render(); }));
document.querySelectorAll('[data-ws]').forEach(b =>
  b.addEventListener('click', () => { state.anyWs = +b.dataset.ws; render(); }));

document.querySelectorAll('[data-preset]').forEach(b =>
  b.addEventListener('click', () => {
    Object.assign(state, PRESETS[b.dataset.preset]);
    $('hold').value = state.holdIdx;
    render();
  }));

$('themeBtn').addEventListener('click', () => {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark'
    || (!document.documentElement.getAttribute('data-theme')
        && matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.setAttribute('data-theme', dark ? 'light' : 'dark');
  $('themeBtn').textContent = dark ? 'Dark mode' : 'Light mode';
});

render();

/* ==================================================================== tabs */
const TABS = [['tabBtnUtil','tabUtil'], ['tabBtnSim','tabSim']];
let simDrawn = false;

function showTab(which){
  TABS.forEach(([btn, panel]) => {
    const on = btn === which;
    $(btn).setAttribute('aria-selected', String(on));
    $(btn).tabIndex = on ? 0 : -1;
    $(panel).hidden = !on;
  });
  if (which === 'tabBtnSim'){
    // the chart is sized to the panel, so it must be (re)drawn while visible
    if (!simDrawn){ simDrawn = true; SIM.init(); } else SIM.redraw();
  }
  try { localStorage.setItem('cct.tab', which); } catch (e) {}
}
TABS.forEach(([btn]) => $(btn).addEventListener('click', () => showTab(btn)));
$('tabBtnUtil').parentElement.addEventListener('keydown', e => {
  if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
  const i = TABS.findIndex(([b]) => $(b).getAttribute('aria-selected') === 'true');
  const next = TABS[(i + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length][0];
  showTab(next); $(next).focus(); e.preventDefault();
});

/* ============================================================= SIMULATION
   One plan date, drawn twice: the Job Sequence that produced it, and the
   trolleys it filled. Stage 4 is recomputed here rather than looked up,
   because the Net_Rate scheme has to be switchable — so it must mirror
   model.py exactly. The parity badge is what proves it still does.
   ====================================================================== */
const SIM = (() => {
const T = DATA.trace, SCOL = DATA.statusColors;
const CAP = A.compartment_cap, SLOTS = A.trolley_compartments;
const MAXB = A.max_batches_per_trolley, BAYS = A.trolley_bays;
const MAXCOMB = A.max_trolleys_per_combine;

// In the order the floor numbers them.
const STATUSES = [
  ['normal',         'Normal condition'],
  ['cut_queue',      'Normal · cut queue'],
  ['stretch',        'Normal · stretch spreading'],
  ['no_pattern',     'No pattern, enough fabric'],
  ['no_fabric_time', 'Have pattern, not enough fabric'],
  ['neither',        'No pattern, not enough fabric'],
  ['no_fabric',      'No fabric'],
  ['completed',      'Completed'],
];
const LABEL = Object.fromEntries(STATUSES);

const sim = {
  date: T.dates[0], mode: 'today', table: DATA.tableLengths[0],
  batches: 1, holdIdx: 0, anyWs: 1, cursor: 0, showAll: false,
  sortBy: 'seq', sortDir: 1,
};

/* ------------------------------------------------------------- the tasks */
function tasksFor(date){
  return T.days[date].tasks.map((r, i) => ({
    i, tableNo: r[0], mo: r[1], style: r[2], color: r[3], batch: r[4], lot: r[5],
    layers: r[6], markerLen: r[7], spreadMin: r[8], cutMin: r[9],
    pieces: r[10], needsTrolleys: !!r[11],
    hasPattern: !!r[12], hasFabric: !!r[13], batchLast: !!r[15],
    // Pull Date is recorded from midnight; everything else on this page is
    // measured from 07:15, so shift it onto the chart's own clock.
    doneAt: r[16] === null ? null : r[16] - A.shift_start_minute,
  }));
}

/* How far the floor ran behind the plan, over every date at once. Counted from
   the trace rather than quoted, so replacing the data cannot leave a stale
   figure in the prose. Record field 16 is the actual finished-spreading time in
   minutes from midnight of the plan date, so 1440 is the end of that date and
   2880 is a further day past it. Counted once — draw() reruns on every control
   change and this never varies. */
const SLIP = (() => {
  const endOfPlanDate = 1440, aFurtherDay = 2 * 1440;
  let dated = 0, late = 0, veryLate = 0;
  for (const date of T.dates)
    for (const r of T.days[date].tasks){
      if (r[16] === null) continue;      // no Pull Date, so it cannot be classified
      dated++;
      if (r[16] > endOfPlanDate) late++;
      if (r[16] > aFurtherDay) veryLate++;
    }
  return {dated, late, veryLate,
          latePct: Math.round(100 * late / dated),
          veryLatePct: Math.round(100 * veryLate / dated)};
})();

/* Fabric relaxing is a hard precondition, not a variable: a table is not
   released to the floor until its fabric has had its 24 hours. So every planned
   table is relaxed, and the two "not enough fabric" statuses stay in the legend
   reading zero. Same for the pattern — the marker ratio is in within 1.5 h of
   the plan being uploaded, so it is never the constraint either.

   Priority matters: finished work is grey whatever else was true of it, and
   "stretch" only qualifies a task that is otherwise normal. */
function statusOf(t, cursor){
  if (t.doneAt !== null && t.doneAt <= cursor) return 'completed';
  if (!t.hasFabric)  return 'no_fabric';
  if (!t.hasPattern) return 'no_pattern';
  return t.batchLast ? 'stretch' : 'normal';
}

/* ------------------------------------------- compartments and trolleys
   Ports of compartments_for / combined_compartments / can_combine /
   _loading_events / load_trolleys in model.py. Maps, not objects, so film
   widths keep Python's insertion order rather than JS's numeric-key order. */
const FILM = A.film_size_by_garment_size;

function compartmentsFor(pieces, film){
  film = film || FILM;
  const out = new Map();
  for (const size of Object.keys(pieces)){
    const qty = pieces[size], f = film[size];
    if (!out.has(f)) out.set(f, []);
    const list = out.get(f);
    for (let k = Math.floor(qty / CAP); k > 0; k--) list.push(CAP);
    const rem = qty % CAP;
    if (rem) list.push(rem);
  }
  return out;
}

function combinedCompartments(a, b, film){
  if (a.batch === b.batch){                       // merge — Panel Loading rule 2
    const merged = {};
    for (const s of Object.keys(a.pieces)) merged[s] = a.pieces[s];
    for (const s of Object.keys(b.pieces)) merged[s] = (merged[s] || 0) + b.pieces[s];
    return compartmentsFor(merged, film);
  }
  const out = new Map();                          // side by side — H1/H4
  for (const t of [a, b])
    for (const [f, list] of compartmentsFor(t.pieces, film))
      out.set(f, (out.get(f) || []).concat(list));
  return out;
}

function trolleysFor(comps){
  let n = 0;
  for (const list of comps.values()) if (list.length) n += Math.ceil(list.length / SLOTS);
  return n;
}

function canCombine(a, b, crossBatch, film){
  if (!a.needsTrolleys || !b.needsTrolleys) return null;
  if (a.mo !== b.mo || a.color !== b.color) return null;
  if (a.batch !== b.batch && !crossBatch)   return null;
  const comps = combinedCompartments(a, b, film);
  if (trolleysFor(comps) > MAXCOMB)         return null;   // H8
  return comps;
}

function loadingEvents(order, time, tasks, crossBatch, film){
  const events = [], pairs = [];
  for (const machine of Object.keys(order)){
    const queue = order[machine];
    let i = 0;
    while (i < queue.length){
      const a = tasks[queue[i]];
      if (!a.needsTrolleys){ i += 1; continue; }
      const b = i + 1 < queue.length ? tasks[queue[i + 1]] : null;
      const paired = b ? canCombine(a, b, crossBatch, film) : null;
      if (paired){
        events.push({when: Math.max(time[a.i][3], time[b.i][3]), task: a, comps: paired,
                     batches: new Set([a.batch, b.batch]), machine, members: [a, b]});
        pairs.push([a.i, b.i]);
        i += 2;
      } else {
        events.push({when: time[a.i][3], task: a, comps: compartmentsFor(a.pieces, film),
                     batches: new Set([a.batch]), machine, members: [a]});
        i += 1;
      }
    }
  }
  events.sort((x, y) => x.when - y.when);          // stable, as Python's is
  return {events, pairs};
}

function loadTrolleys(events, hold, anyWs){
  const parked = new Map();                        // key -> [trolley, ...]
  const trolleys = [];
  let compsUsed = 0, pieces = 0, combines = 0, blockedBySpace = 0;
  const waits = [];
  const parkedNow = () => { let n = 0; for (const v of parked.values()) n += v.length; return n; };

  for (const ev of events){
    if (ev.batches.size > 1) combines++;

    for (const [k, arr] of parked){                // send away what has waited
      const keep = [];
      for (const tr of arr){
        if (ev.when - tr.at <= hold) keep.push(tr);
        else { waits.push(ev.when - tr.at); tr.left = ev.when; }
      }
      parked.set(k, keep);
    }

    for (const [f, list] of ev.comps){
      if (!list.length) continue;
      compsUsed += list.length;
      for (const q of list) pieces += q;

      // MO + colour + film size (H4). Batch is deliberately NOT in the key -
      // that is the whole point of change 2.
      const key = [ev.task.mo, ev.task.color, f].join(' ')
                + (anyWs ? '' : ' ' + ev.machine);
      let need = list.length;
      const waiting = list.slice();                // for drawing only
      const arr = parked.get(key) || [];

      for (const tr of arr){                       // (a) top up what is parked
        if (need === 0) break;
        const would = new Set([...tr.batches, ...ev.batches]);
        if (would.size > MAXB) continue;           // would be a third batch
        const take = Math.min(tr.free, need);
        if (take === 0) continue;
        tr.free -= take; tr.batches = would; need -= take;
        for (const q of waiting.splice(0, take))
          tr.comps.push({qty: q, batch: ev.task.batch, table: ev.task.tableNo,
                         recalled: true});
      }
      parked.set(key, arr.filter(tr => tr.free > 0));

      while (need > 0){                            // (b) open fresh trolleys
        const take = Math.min(SLOTS, need);
        need -= take;
        const tr = {film: f, free: SLOTS - take, at: ev.when, comps: [],
                    batches: new Set(ev.batches), mo: ev.task.mo, color: ev.task.color,
                    parked: false, left: null};
        for (const q of waiting.splice(0, take))
          tr.comps.push({qty: q, batch: ev.task.batch, table: ev.task.tableNo,
                         recalled: false});
        trolleys.push(tr);
        if (tr.free > 0 && hold > 0){
          if (parkedNow() < BAYS){
            tr.parked = true;
            if (!parked.has(key)) parked.set(key, []);
            parked.get(key).push(tr);
          } else blockedBySpace++;
        }
      }
    }
  }

  const util = trolleys.length ? 100 * compsUsed / (SLOTS * trolleys.length) : 0;
  return {trolleys, compartments: compsUsed, pieces, combines, blockedBySpace,
          util, avgWaitHours: waits.length ? waits.reduce((a, b) => a + b, 0) / waits.length / 60 : 0};
}

/* ---------------------------------------------------------- run one day */
function simulate(){
  const seq = T.days[sim.date].seq[sim.mode];
  const buf = seq.table[sim.table];
  const tasks = tasksFor(sim.date);
  const {events, pairs} = loadingEvents(seq.order, buf.time, tasks,
                                        sim.batches >= 2, FILM);
  const result = loadTrolleys(events, HOLDS[sim.holdIdx], sim.anyWs);
  return {tasks, seq, time: buf.time, expected: buf.expected, blocked: buf.blocked,
          events, pairs, ...result};
}

/* ------------------------------------------------------------- the Gantt */
function ganttRows(){
  const rows = [];
  for (const cut of Object.keys(DATA.cutGroups)){
    for (const m of DATA.cutGroups[cut])
      rows.push({key: 'S' + m, label: 'SPD ' + m, kind: 'spd', name: m});
    rows.push({key: 'C' + cut, label: 'CUT ' + cut.replace('24', ''), kind: 'cut', name: cut});
    rows.push({kind: 'gap'});
  }
  rows.pop();
  return rows;
}

/* Minutes on the timeline are measured from the start of the day shift, so
   t = 0 is 07:15 and the axis reads in real clock time. The Pull Date arrives
   measured from midnight, so tasksFor() shifts it onto this clock. */
const SHIFT_START = A.shift_start_minute;

function hhmm(minutesFromMidnight){
  const m = ((minutesFromMidnight % 1440) + 1440) % 1440;
  return String(Math.floor(m / 60)).padStart(2, '0') + ':'
       + String(Math.round(m % 60)).padStart(2, '0');
}
// t is minutes from 07:15
const clock = t => {
  const abs = t + SHIFT_START, d = Math.floor(abs / 1440);
  return (d > 0 ? `+${d}d ` : '') + hhmm(abs);
};
// Staffed minutes between two instants — so a gap on the chart can be split
// into "starved" (G6) and "nobody here" (break, or shift over).
function workingBetween(spans, a, b){
  let n = 0;
  for (const [s, e] of spans || []) n += Math.max(0, Math.min(b, e) - Math.max(a, s));
  return n;
}

// The eight status colours are a mix of pale and dark, so pick the label
// colour from the swatch's luminance rather than assuming.
function inkOn(hex){
  const n = parseInt(hex.slice(1), 16);
  const lum = (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
  return lum > 0.6 ? '#101720' : '#FFFFFF';
}

/* How wide to draw. The panel decides; 1120 is the floor, below which the
   chart scrolls inside its container rather than becoming unreadable. */
const GANTT_MIN_WIDTH = 1120;
function ganttWidth(){
  const box = $('gantt').parentElement;      // .ganttinner
  return Math.max(GANTT_MIN_WIDTH, Math.round(box.clientWidth) || GANTT_MIN_WIDTH);
}

/* Where the chart stops. The night machines are staffed until 05:00, but on most
   days the last cut is long before that — running the axis to 05:00 regardless
   leaves hours of empty grey and squeezes the work. End at the last thing that
   happens, rounded up to the hour, never earlier than the day shift. */
function ganttEnd(run){
  let last = 0;
  for (const i in run.time) last = Math.max(last, run.time[i][3]);
  return Math.max(DATA.dayShiftEnd, Math.ceil(last / 60) * 60);
}

function gantt(run){
  const rows = ganttRows(), time = run.time, order = run.seq.order;
  // Drawn at the panel's own width — no scaling, so the rows keep their height
  // and the labels their size however wide the window is.
  const W = ganttWidth(), L = 96, R = 14, H_ROW = 23, H_GAP = 9;
  const xmax = ganttEnd(run);
  const x = v => L + (W - L - R) * v / xmax;

  let y = 26, top = {};
  for (const r of rows){ if (r.kind !== 'gap') top[r.key] = y; y += r.kind === 'gap' ? H_GAP : H_ROW; }
  const H = y + 8;

  const paired = new Map();
  run.pairs.forEach(([a, b]) => { paired.set(a, b); });

  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img"
    aria-label="Job sequence for ${sim.date}: ${run.tasks.length} tables across 13 spreading machines">
    <defs><pattern id="blk" width="5" height="5" patternUnits="userSpaceOnUse"
      patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="5" stroke="var(--bad)" stroke-width="1.6" opacity=".45"/>
    </pattern></defs>`;

  // hour grid, in real clock time from 07:15
  for (let t = (60 - SHIFT_START % 60) % 60; t <= xmax; t += 60){
    const onHour = (t + SHIFT_START) % 120 === 0;
    s += `<line x1="${x(t)}" x2="${x(t)}" y1="20" y2="${H - 6}" stroke="var(--rule)"
           stroke-width="1"/>`;
    if (onHour)
      s += `<text x="${x(t)}" y="14" text-anchor="middle" class="num" font-size="9.5"
             fill="var(--muted)">${clock(t)}</text>`;
  }

  // when each machine is actually staffed — outside it, and through breaks,
  // the row is dead. Day-only machines stop at 20:00; 24-01/02/03 run to 05:00.
  for (const r of rows){
    if (r.kind === 'gap') continue;
    const spans = (r.kind === 'spd' ? DATA.spreaderShift : DATA.cutterShift)[r.name] || [];
    const ry = top[r.key];
    let cursor = 0;
    for (const [from, to] of spans){
      if (from > cursor)
        s += `<rect x="${x(cursor)}" y="${ry}" width="${x(from) - x(cursor)}"
               height="${H_ROW - 3}" fill="var(--rule2)" opacity=".28"><title>Break</title></rect>`;
      cursor = to;
    }
    if (cursor < xmax)
      s += `<rect x="${x(cursor)}" y="${ry}" width="${x(xmax) - x(cursor)}"
             height="${H_ROW - 3}" fill="var(--rule2)" opacity=".28"><title>Not staffed — this machine's shift ended at ${clock(cursor)}</title></rect>`;
    s += `<text x="0" y="${ry + 13}" font-size="10" class="num"
           fill="var(--${r.kind === 'cut' ? 'ink' : 'muted'})"
           font-weight="${r.kind === 'cut' ? 600 : 400}">${r.label}</text>`;
    s += `<line x1="${L}" x2="${W - R}" y1="${ry + H_ROW - 3}"
           y2="${ry + H_ROW - 3}" stroke="var(--rule)" stroke-width="1"
           opacity="${r.kind === 'cut' ? 1 : .45}"/>`;
  }

  // bars
  for (const machine of Object.keys(order)){
    const queue = order[machine];
    let prevEnd = null;
    for (const idx of queue){
      const t = run.tasks[idx], tm = time[idx];
      const [ss, se, cs, ce, cutter] = tm;
      const st = t._st, col = SCOL[st];
      const rowY = top['S' + machine];

      // G6 blocking — but only the part of the gap the machine was actually
      // staffed for. Time lost to a break or to the shift ending is drawn by
      // the shift bands, and is not the machine being starved.
      if (prevEnd !== null && ss - prevEnd > 0.5){
        const idle = workingBetween(DATA.spreaderShift[machine], prevEnd, ss);
        if (idle > 0.5)
          s += `<rect x="${x(prevEnd)}" y="${rowY + 3}" width="${Math.max(1, x(ss) - x(prevEnd))}"
                 height="${H_ROW - 9}" fill="url(#blk)"><title>Blocked ${Math.round(idle)} min — not enough table free for the next lay (G6)</title></rect>`;
      }
      prevEnd = se;

      const tip = `${t.tableNo} · ${t.mo} · ${t.color} · batch ${t.batch}`
        + ` · ${t.layers} layers · spread ${Math.round(t.spreadMin)} min`
        + ` · cut ${Math.round(t.cutMin)} min · ${clock(ss)}–${clock(se)} · ${LABEL[st]}`;

      const w = Math.max(1, x(se) - x(ss));
      s += `<rect x="${x(ss)}" y="${rowY + 2}" width="${w}"
             height="${H_ROW - 7}" rx="1.5" fill="${col}" stroke="rgba(16,23,32,.35)"
             stroke-width=".6"><title>SPD ${machine} — ${tip}</title></rect>`;
      // the table number, when the bar is wide enough to hold it
      const name = String(t.tableNo == null ? '' : t.tableNo);
      if (w >= name.length * 5.6 + 6)
        s += `<text x="${x(ss) + w / 2}" y="${rowY + H_ROW / 2 + 1}" text-anchor="middle"
               class="num" font-size="8.5" font-weight="600" fill="${inkOn(col)}"
               pointer-events="none">${name}</text>`;

      const cutY = top['C' + cutter];
      s += `<rect x="${x(cs)}" y="${cutY + 4}" width="${Math.max(1, x(ce) - x(cs))}"
             height="${H_ROW - 11}" rx="1.5" fill="${col}" opacity=".62"
             stroke="rgba(16,23,32,.3)" stroke-width=".6"><title>CUT ${cutter} — ${tip}</title></rect>`;

      // the pair bracket — this is what change 1 creates
      if (paired.has(idx)){
        const other = time[paired.get(idx)];
        if (other){
          const x1 = x(ss), x2 = x(Math.max(se, other[1])), by = rowY - 1;
          s += `<path d="M${x1} ${by + 3} L${x1} ${by} L${x2} ${by} L${x2} ${by + 3}"
                 fill="none" stroke="var(--ink)" stroke-width="1.2" opacity=".8"/>`;
        }
      }
    }
  }

  // the time cursor, on the same axis as the slider above it
  if (sim.cursor > 0 && sim.cursor <= xmax){
    s += `<line x1="${x(sim.cursor)}" x2="${x(sim.cursor)}" y1="18" y2="${H - 4}"
           stroke="var(--s1)" stroke-width="1.5"/>`;
    s += `<text x="${x(sim.cursor)}" y="${H - 6}" text-anchor="middle" class="num"
           font-size="9" fill="var(--s1)" font-weight="600">${clock(sim.cursor)}</text>`;
  }
  return s + '</svg>';
}

/* Which table went onto which trolley, and how full each one left. */
function trolleyTable(run){
  let h = `<thead><tr><th>Trolley</th><th>Film</th><th class="n">Compartments</th>
    <th class="n">Fill</th><th class="n">Pieces</th><th>Batches</th><th>Tables it carries</th>
    <th>Left at</th></tr></thead><tbody>`;
  run.trolleys.forEach((tr, i) => {
    const used = tr.comps.length;
    const pieces = tr.comps.reduce((n, c) => n + c.qty, 0);
    const tables = [...new Set(tr.comps.map(c => c.table))];
    const fill = 100 * used / SLOTS;
    h += `<tr><td class="num">#${String(i + 1).padStart(3, '0')}</td>`
      + `<td class="num">${tr.film}</td>`
      + `<td class="n">${used} of ${SLOTS}</td>`
      + `<td class="n" style="color:${fill >= 80 ? 'var(--s2)' : fill <= 40 ? 'var(--bad)' : 'inherit'}">`
      + `${fill.toFixed(0)}%</td>`
      + `<td class="n">${pieces}</td>`
      + `<td class="num">${[...tr.batches].join(', ')}</td>`
      + `<td class="num">${tables.join(', ')}</td>`
      + `<td class="num">${tr.parked ? 'held in WIP' : clock(tr.at)}</td></tr>`;
  });
  return h + '</tbody>';
}

/* ----------------------------------------------------------- the trolleys */
function trolleyCards(run){
  const byFilm = new Map();
  run.trolleys.forEach(tr => {
    if (!byFilm.has(tr.film)) byFilm.set(tr.film, []);
    byFilm.get(tr.film).push(tr);
  });
  const films = [...byFilm.keys()].sort((a, b) => a - b);
  const LIMIT = 60;
  let html = '';

  for (const f of films){
    const list = byFilm.get(f);
    const shown = sim.showAll ? list : list.slice(0, LIMIT);
    const full = list.filter(t => t.free === 0).length;
    html += `<div class="filmhead">FILM ${f} &mdash; ${list.length} trolleys,
             ${full} of them full`
          + (shown.length < list.length ? `, showing ${shown.length}` : '') + `</div>`;
    html += '<div class="trolleyrow">';
    for (const tr of shown){
      const tints = [...tr.batches];
      html += `<div class="tcard"><div class="h"><span>${tr.mo ? String(tr.mo).slice(-5) : ''}</span>`
            + `<span>${tr.comps.length}/${SLOTS}</span></div>`;
      for (let k = SLOTS - 1; k >= 0; k--){
        const c = tr.comps[k];
        if (!c){ html += '<div class="c empty"></div>'; continue; }
        const tint = tints.indexOf(c.batch) === 0 ? 'var(--s2)' : 'var(--s3)';
        html += `<div class="c" style="background:${tint}" title="batch ${c.batch}`
              + `${c.recalled ? ' — loaded after recall from WIP' : ''}">`
              + `<span>${c.qty}</span><span>${tints.length > 1 ? (tints.indexOf(c.batch) + 1) : ''}</span></div>`;
      }
      html += `<div class="h" style="margin:5px 0 0"><span>${tr.batches.size} batch`
            + `${tr.batches.size > 1 ? 'es' : ''}</span>`
            + `<span>${tr.parked ? 'held' : ''}</span></div></div>`;
    }
    html += '</div>';
  }
  const total = run.trolleys.length;
  if (!sim.showAll && total > LIMIT)
    html += `<p class="hint" style="margin-top:14px">Showing the first ${LIMIT} trolleys per
             film width, of ${total} for the day.
             <button type="button" id="showAll" class="theme" style="padding:4px 9px">Show all</button></p>`;
  return html;
}

/* ------------------------------------------------------------ the table */
const COLS = [
  ['seq',    'Status',   t => `<span class="dot" style="background:${SCOL[t._st]}"></span>${LABEL[t._st]}`, false],
  ['table',  'Table',    t => t.tableNo, false],
  ['mo',     'MO',       t => t.mo, false],
  ['style',  'Style',    t => t.style || '', false],
  ['color',  'Colour',   t => t.color, false],
  ['batch',  'Batch',    t => t.batch, false],
  ['machine','Machine',  t => t._machine || '—', false],
  ['start',  'Spread',   t => t._ss === undefined ? '' : clock(t._ss) + '–' + clock(t._se), true],
  ['lot',    'Lot',      t => t.lot == null ? '' : t.lot, false],
  ['layers', 'Layers',   t => t.layers, true],
  ['len',    'Marker m', t => t.markerLen.toFixed(1), true],
  ['smin',   'Spd min',  t => Math.round(t.spreadMin), true],
  ['cmin',   'Cut min',  t => Math.round(t.cutMin), true],
  ['pieces', 'Pieces',   t => t._pieces || '—', true],
  ['comps',  'Comps',    t => t.needsTrolleys ? t._comps : '—', true],
];
const SORTVAL = {
  seq: t => STATUSES.findIndex(s => s[0] === t._st),
  table: t => String(t.tableNo), mo: t => String(t.mo), style: t => String(t.style || ''),
  color: t => String(t.color), batch: t => String(t.batch),
  machine: t => String(t._machine || ''), start: t => (t._ss === undefined ? 1e9 : t._ss),
  lot: t => String(t.lot == null ? '' : t.lot),
  layers: t => t.layers, len: t => t.markerLen, smin: t => t.spreadMin, cmin: t => t.cutMin,
  pieces: t => t._pieces || 0, comps: t => t._comps || 0,
};

function taskTable(run){
  const rows = run.tasks.slice();
  rows.sort((a, b) => {
    const va = SORTVAL[sim.sortBy](a), vb = SORTVAL[sim.sortBy](b);
    if (va < vb) return -sim.sortDir;
    if (va > vb) return sim.sortDir;
    return a.i - b.i;
  });
  let h = '<thead><tr>' + COLS.map(([k, label,, num]) =>
    `<th data-sort="${k}" class="${num ? 'n' : ''}">${label}`
    + (sim.sortBy === k ? (sim.sortDir > 0 ? ' ↑' : ' ↓') : '') + '</th>').join('') + '</tr></thead><tbody>';
  for (const t of rows)
    h += '<tr>' + COLS.map(([, , fn, num]) =>
      `<td class="${num ? 'n' : ''}">${fn(t)}</td>`).join('') + '</tr>';
  return h + '</tbody>';
}

/* ---------------------------------------------------------------- render */
function draw(){
  const run = simulate();
  const day = T.days[sim.date];

  // decorate tasks for the table
  const time = run.time;
  for (const machine of Object.keys(run.seq.order))
    for (const idx of run.seq.order[machine]){
      const t = run.tasks[idx];
      t._machine = machine; t._ss = time[idx][0]; t._se = time[idx][1];
    }
  for (const t of run.tasks){
    t._st = statusOf(t, sim.cursor);
    t._pieces = Object.values(t.pieces).reduce((a, b) => a + b, 0);
    t._comps = t.needsTrolleys ? [...compartmentsFor(t.pieces).values()]
                                   .reduce((n, l) => n + l.length, 0) : 0;
  }

  $('ganttDate').textContent = sim.date;
  $('listDate').textContent = sim.date;
  $('gantt').innerHTML = gantt(run);
  $('taskTable').innerHTML = taskTable(run);
  $('trolleyTable').innerHTML = trolleyTable(run);
  $('trolleys').innerHTML = trolleyCards(run);
  const showAllBtn = $('showAll');
  if (showAllBtn) showAllBtn.addEventListener('click', () => { sim.showAll = true; draw(); });

  $('loadSummary').textContent =
    `${run.trolleys.length} trolleys · ${run.util.toFixed(1)}% full · ${run.combines} combines`;
  $('taskSummary').textContent =
    `${run.tasks.length} tables · ${Math.round(run.tasks.reduce((n, t) => n + t.spreadMin, 0))} spreading minutes`;

  // status legend, with the two that cannot fire called out
  const counts = {};
  for (const t of run.tasks) counts[t._st] = (counts[t._st] || 0) + 1;
  $('statusLegend').innerHTML = STATUSES.map(([k, label]) => {
    const why = DATA.statusNotSimulated[k];
    return `<span class="${counts[k] ? '' : 'off'}" ${why ? `title="not simulated — ${why}"` : ''}>`
      + `<i style="background:${SCOL[k]}"></i>${label} <b>${counts[k] || 0}</b>`
      + (why ? ' <span class="muted">(not simulated)</span>' : '') + '</span>';
  }).join('');

  $('dayMeta').innerHTML = `<b>${run.tasks.length}</b> tables modelled`
    + (day.skipped ? `, ${day.skipped} skipped as Type C or first table (J2)` : '')
    + `. ${run.tasks.filter(t => !t.needsTrolleys).length} carry no compartments (J3).`;

  $('taskNote').innerHTML = `Compartments are what the table needs on its own.
    Tables that combine share fewer &mdash; that is what Panel Loading below shows.`;

  // ---- idle time, the thing the hatching is measuring
  const base = run.seq.table[DATA.tableLengths[0]].blocked;
  $('idleNote').innerHTML = sim.table === DATA.tableLengths[0]
    ? `Hatching is rule G6: the spreader has stopped because the lay in front has not
       yet been cut far enough to free ${sim.table} m of table.
       <b>${Math.round(base)} minutes</b> lost across 13 machines today. At
       ${DATA.tableLengths[1]} m of table it falls to
       <b>${Math.round(run.seq.table[DATA.tableLengths[1]].blocked)}</b>.`
    : `With a ${sim.table} m table, blocking is
       <b>${Math.round(run.blocked)} minutes</b> today, against
       <b>${Math.round(base)}</b> at today's ${DATA.tableLengths[0]} m &mdash;
       <b>${Math.round(100 * (1 - run.blocked / base))}% less</b>. See
       <code>IDLE_TIME.md</code>.`;

  /* ---- how far the floor ran behind the plan. `doneAt` is on the chart's
     clock, which starts at 07:15, so midnight at the end of the plan date is
     1440 − shift_start_minute. The dataset-wide shares come from SLIP, which
     counts the same thing across every date. */
  const midnight = 1440 - SHIFT_START;
  const late = run.tasks.filter(t => t.doneAt !== null && t.doneAt > midnight).length;
  $('slipNote').innerHTML = `<b>${late}</b> of ${run.tasks.length} tables were not
    actually spread until after ${sim.date}. Across all ${T.dates.length} dates,
    <b>${SLIP.latePct}%</b> of ${SLIP.dated} tables finish after their plan date and
    <b>${SLIP.veryLatePct}%</b> more than a day late.`;

  // ---- does this page still agree with the model?
  const k = key(sim.mode === 'mo_aware' ? 1 : 0, sim.batches, HOLDS[sim.holdIdx], sim.anyWs);
  const exp = run.expected[k];
  const p = $('parity');
  if (exp && Math.abs(exp[0] - run.util) < 0.011 && exp[1] === run.trolleys.length){
    p.className = 'parity ok';
    p.innerHTML = `&#10003; Matches the model &mdash; <span class="num">${run.trolleys.length}</span>
      trolleys, <span class="num">${run.util.toFixed(1)}%</span> full, same as
      <code>run.py</code> for this day and these settings.`;
  } else {
    p.className = 'parity bad';
    p.innerHTML = `&#9888; This page and <code>run.py</code> disagree for this day: page says
      <span class="num">${run.trolleys.length}</span> trolleys / <span class="num">${run.util.toFixed(1)}%</span>,
      the model says <span class="num">${exp ? exp[1] : '?'}</span> /
      <span class="num">${exp ? exp[0].toFixed(1) : '?'}%</span>. Trust the model.`;
  }

  // ---- control labels
  $('seqVal').textContent = sim.mode === 'today' ? 'off' : 'on';
  $('simBatchVal').textContent = sim.batches;
  $('bufVal').textContent = sim.table + ' m';
  $('simHoldVal').textContent = HOLDS[sim.holdIdx] === 0 ? 'off' : HOLDS[sim.holdIdx] + ' min';
  $('simWsVal').textContent = sim.anyWs ? 'any workstation' : 'same only';
  $('cursorVal').textContent = clock(sim.cursor);
  $('simWsField').style.opacity = HOLDS[sim.holdIdx] === 0 ? .4 : 1;
  $('simWsField').querySelectorAll('button').forEach(b => b.disabled = HOLDS[sim.holdIdx] === 0);
  document.querySelectorAll('[data-seq]').forEach(b =>
    b.setAttribute('aria-pressed', String(b.dataset.seq === sim.mode)));
  document.querySelectorAll('[data-simbatch]').forEach(b =>
    b.setAttribute('aria-pressed', String(+b.dataset.simbatch === sim.batches)));
  document.querySelectorAll('[data-table]').forEach(b =>
    b.setAttribute('aria-pressed', String(b.dataset.table === sim.table)));
  document.querySelectorAll('[data-simws]').forEach(b =>
    b.setAttribute('aria-pressed', String(+b.dataset.simws === sim.anyWs)));
  document.querySelectorAll('[data-day]').forEach(b =>
    b.setAttribute('aria-pressed', String(b.dataset.day === sim.date)));
}

/* ------------------------------------------------------------ the wiring */
function buildCalendar(){
  const dates = T.dates, first = new Date(dates[0] + 'T00:00:00');
  const year = first.getFullYear(), month = first.getMonth();
  $('calMonth').textContent = first.toLocaleDateString('en-US', {month: 'long', year: 'numeric'});
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const lead = (new Date(year, month, 1).getDay() + 6) % 7;      // Monday first
  let h = ['Mo','Tu','We','Th','Fr','Sa','Su'].map(d => `<div class="dow">${d}</div>`).join('');
  for (let i = 0; i < lead; i++) h += '<span></span>';
  for (let d = 1; d <= daysInMonth; d++){
    const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    h += dates.includes(iso)
      ? `<button type="button" data-day="${iso}" aria-pressed="${iso === sim.date}"
          title="${iso}">${d}</button>`
      : `<span title="not in the data">${d}</span>`;
  }
  $('calendar').innerHTML = h;
  $('calendar').querySelectorAll('[data-day]').forEach(b =>
    b.addEventListener('click', () => {
      sim.date = b.dataset.day; sim.showAll = false; draw(); resetCursor(simulate());
    }));
}

/* The cursor greys out work that has actually finished spreading, using the
   recorded Pull Date. It runs on the chart's own axis — 07:15 to wherever the
   day ends — so the handle sits over the hour it selects.

   It has to run PAST the end of the simulated day. `doneAt` is the actual
   finished-spreading time, and on 2026-05-04 twenty-three of sixty-two tables
   finish after the plan ends, the latest 2.5 days later; capped at the chart's
   end they could never be dragged to grey. Three days is the ceiling — which
   does not reach every tail: on 12 of the 20 dates some work finishes later
   still. A slider long enough for the worst of them would be too coarse to be
   useful on any of them. */
const CURSOR_MAX_MINUTES = 3 * 1440;
function resetCursor(run){
  let lastDone = 0;
  for (const t of run.tasks) if (t.doneAt !== null) lastDone = Math.max(lastDone, t.doneAt);
  const el = $('cursor');
  el.min = 0;
  el.max = Math.min(CURSOR_MAX_MINUTES,
                    Math.max(ganttEnd(run), Math.ceil(lastDone / 60) * 60));
  el.step = 15;
  el.value = 0;
  sim.cursor = 0;
}

function init(){
  buildCalendar();
  document.querySelectorAll('[data-seq]').forEach(b =>
    b.addEventListener('click', () => { sim.mode = b.dataset.seq; draw(); }));
  document.querySelectorAll('[data-simbatch]').forEach(b =>
    b.addEventListener('click', () => { sim.batches = +b.dataset.simbatch; draw(); }));
  $('tableSeg').innerHTML = DATA.tableLengths.map(m =>
    `<button type="button" data-table="${m}" aria-pressed="${m === sim.table}">${m} m</button>`).join('');
  $('tableSeg').querySelectorAll('[data-table]').forEach(b =>
    b.addEventListener('click', () => { sim.table = b.dataset.table; draw(); }));
  document.querySelectorAll('[data-simws]').forEach(b =>
    b.addEventListener('click', () => { sim.anyWs = +b.dataset.simws; draw(); }));
  $('simHold').addEventListener('input', e => { sim.holdIdx = +e.target.value; draw(); });

  // the chart is drawn at the panel's width, so it has to be redrawn when that
  // changes — but only when it is on screen, and not on every resize frame
  let resizeTimer = null, lastWidth = 0;
  addEventListener('resize', () => {
    if ($('tabSim').hidden) return;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const w = ganttWidth();
      if (w !== lastWidth){ lastWidth = w; draw(); }
    }, 120);
  });
  $('cursor').addEventListener('input', e => { sim.cursor = +e.target.value; draw(); });
  $('taskTable').addEventListener('click', e => {
    const th = e.target.closest('th[data-sort]');
    if (!th) return;
    if (sim.sortBy === th.dataset.sort) sim.sortDir *= -1;
    else { sim.sortBy = th.dataset.sort; sim.sortDir = 1; }
    draw();
  });

  draw();
  resetCursor(simulate());
}

return {init, redraw: () => { if (typeof draw === 'function') draw(); }};
})();

try {
  const saved = localStorage.getItem('cct.tab');
  if (saved && TABS.some(([b]) => b === saved)) showTab(saved);
} catch (e) {}
</script>
</body>
</html>
"""
