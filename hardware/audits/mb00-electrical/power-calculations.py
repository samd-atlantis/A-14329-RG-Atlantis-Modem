"""Conditional engineering estimates only; no electrical simulation or signoff."""
import json
from pathlib import Path

vout, vin, fsw = 3.3, 5.25, 2.5e6
lmin = 1e-6 * 0.8
ripple = vout * (1 - vout / vin) / (lmin * fsw)
data = {
    "status": "UNVALIDATED_ENGINEERING_ESTIMATES",
    "assumptions": {
        "vin_V": vin, "vout_V": vout, "fsw_typical_Hz": fsw,
        "candidate_L_nominal_H": 1e-6, "candidate_L_minimum_assumed_H": lmin,
        "buck_efficiency_assumed": 0.85, "extra_5V_power_allowance_W": 0.5,
        "router_budget_A_at_3V3": 1.0,
        "warning": "Frequency, efficiency, effective L/C, ESR and load are not measured."
    },
    "ripple_estimate_App": ripple,
    "peak_estimates": [], "startup_estimates": [], "power_budget_estimates": [],
    "TI_matrix_observations": {
        "conditions": "12V input,3.3V output,1A load,high frequency;ceramic effective=half nominal",
        "L_2p2uH": {"Ceff_200uF": "stable_outside_recommendation", "Ceff_400uF": "unstable", "Ceff_800uF": "unstable"},
        "L_1uH": {"Ceff_400uF": "stable_outside_recommendation", "Ceff_800uF": "unstable"},
        "interpolation_permitted_as_signoff": False
    }
}
for load in (2.7, 3.0):
    peak = load + ripple / 2
    data["peak_estimates"].append({"load_A": load, "peak_A": peak,
                                   "Isat_screening_with_20pct_allowance_A": peak*1.2})
for css in (3.3e-9, 22e-9):
    tss = 1.25 * css / 2.5e-6
    for cout in (116e-6, 586e-6):
        data["startup_estimates"].append({"CSS_F": css, "COUT_nominal_F": cout,
             "tSS_s": tss, "capacitor_only_current_A": cout*vout/tss})
for modem, router in ((2.7,1.0),(3.0,1.0),(3.0,3.0)):
    p = (modem+router)*vout/0.85 + 0.5
    data["power_budget_estimates"].append({"modem_A":modem,"router_A":router,
        "5V_power_W":p,"5V_current_A":p/5,
        "headroom_fraction_at_20W":1-p/20,"headroom_fraction_at_18W":1-p/18,
        "exceeds_60C_14W_approximation":p>14})
path=Path(__file__).with_suffix('.json')
path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(path)
