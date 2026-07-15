# System Conditions for Offshore Electricity Storage

A spatially resolved, cost-minimising capacity-expansion model of the **Dutch power system in 2040**, built in [Calliope](https://calliope.readthedocs.io/) 0.6.10, used to identify the system conditions under which **offshore battery storage** reduces total system cost.

This repository contains the model that supports the MSc thesis:

> **System Conditions for Offshore Electricity Storage** — *A system-level assessment of cost-effectiveness and system impacts in a high offshore wind Dutch power system*
> Marijn van Tienhoven, MSc Complex Systems Engineering & Management, TU Delft, June 2026.
> In collaboration with **RWE**, within the **OESTER** (Offshore Electricity Storage Technology Research) project.

This model lives at `Thesis Marijn/DELFTBLUE_SET` inside the [`rwe-thesis-project`](https://github.com/Mvantienhoven/rwe-thesis-project) repository:

```
Thesis Marijn/
├── DELFTBLUE_SET/       # ← this model: config, runfiles, SLURM scripts
├── Postprocessing/      #   analysis of the NetCDF results
├── analysis_results/    #   processed outputs
└── Tekst bronnen/       #   source material
```

Folders at the repository root (`Calliope_Dutch_Model_KH_ServerCopy`, `Calliope_Model_Original`, `NBNL-Data-Overdracht`, `NBNL2025-Decentralised`) are upstream and background material, not part of this thesis — see [Legacy code and provenance](#legacy-code-and-provenance).

```bash
git clone https://github.com/Mvantienhoven/rwe-thesis-project.git
cd "rwe-thesis-project/Thesis Marijn/DELFTBLUE_SET"
```

---

## What the model does

Offshore wind expansion in the Netherlands creates a **spatial mismatch** (generation offshore, demand onshore) and a **temporal mismatch** (variable wind vs. demand). Offshore storage is the only response option that sits *upstream* of the export cable, so it can relieve export-cable congestion that onshore storage — sitting behind the cable — cannot.

The model minimises **total annualised system cost** (CAPEX + fixed/variable OPEX + fuel + CO₂ + network expansion) over a full year at 3-hourly resolution, letting generation, storage, transmission, export cables and landing-point build-out **compete endogenously**. It is run across a 3×3×3 scenario design to find when the cost-optimal system chooses to put storage offshore.

**Main research question:** *Under which system conditions does offshore electricity storage reduce total system costs in the 2040 Dutch power system with increased offshore wind capacity?*

---

## Model at a glance

| | |
|---|---|
| Framework | Calliope 0.6.10 (LP, `plan` mode) |
| Solver | Gurobi 12.0.0 (barrier, no crossover) |
| Year / resolution | 2040, 3-hourly (2,928 timesteps — 2040 is a leap year) |
| Weather year | 2012 (NBNL/PECD) |
| Demand | 302.3 TWh, fixed hourly profile (no demand response) |
| Objective | Minimise annualised monetary system cost |
| ETS price | 177 €/tCO₂ |
| Scenario background | NBNL Energy Transition Model — *Koersvaste Middenweg* (hence the `KM` suffix throughout) |
| Compute | DelftBlue (TU Delft HPC), SLURM |

The model is **electricity-only**. Hydrogen, heat, SMRs and electrolysers are present in the config but **commented out** — see [Legacy code](#legacy-code-and-provenance).

### Spatial structure

- **33 inland nodes** (`E-*`) — Dutch 380 kV switching/transformer substations, present or under construction in 2025
- **6 offshore wind hubs** (`O-*`) — Noorden Waddeneilanden + Doordewind, Nederwiek, IJmuiden Ver + Lagelander, Hollandse Kust, Borssele, Gebied 6/7 (individual parks clustered by coordinates and export-cable route)
- **5 landing points** (`L-*`) — Eemshaven, Noord-Holland, Rotterdam, Geertruidenberg, Borssele (DC→AC converter stations)
- **9 foreign nodes** — DE, BE, UK, NO, DK interconnection
- **71 edges** — 51 onshore HVAC lines + interconnectors, offshore HVDC export cables, and landing-interface links. One hybrid interconnector (LionLink, `E-UK ↔ O-NEW`).

Landing-point build-out is **not** a separate asset class: its capacity limits and costs sit on the inland links between landing points and inland substations (`L-* ↔ E-*`).

### Technologies

- **Renewables** — offshore wind, onshore wind, rooftop PV, utility PV, run-of-river hydro
- **Dispatchable** — conventional nuclear, CCGT, OCGT, biomass, waste incineration
- **Storage** — lithium-ion BESS: `ES_BESS_IDES` (onshore + landing points) and `ES_BESS_offshore` (offshore hubs). 85% round-trip, 15-year lifetime.
- **Transmission** — HVAC onshore (0.4 M€/GW/km), HVDC offshore (174 M€/GW + 2.6 M€/GW-km, incl. platform and converter)

Thermal plants are fed by a single free `fuel_dummy` carrier, with fuel + ETS + VOM folded into one all-in `om_prod` (e.g. CCGT at 130.15 €/MWh_e) and CO₂ tracked as a separate output carrier into a sink. This keeps the model power-only without needing a gas network.

---

## Scenario design

Three conditions are varied (3 × 3 × 3 = **27 scenarios**). Each is run twice — offshore storage **enabled** and **disabled** — giving **54 runs**. The disabled run is the counterfactual used to isolate offshore storage's contribution.

**This repository defines the 27 enabled scenarios only.** The disabled runs were produced by manually commenting out offshore storage in the YAML — see [Reproducing the disabled runs](#reproducing-the-disabled-runs).

| Dimension | Levels | Thesis label |
|---|---|---|
| **W** — offshore wind capacity (lower bound) | 30 / 37.5 / 45 GW | W30 / W37.5 / W45 |
| **L** — near-landing onshore storage (cap per node) | 0 / 560 MWh / unconstrained | L_no / L_lim / L_unc |
| **P** — offshore storage cost premium vs. onshore | 0% / 25% / 75% | P0 / P25 / P75 |

Offshore wind upper bound is fixed at ~50 GW across all runs. Export cable capacity can expand to 50 GW; existing landing and export capacity is 30 GW, expandable to 40 GW. The 45 GW wind case deliberately exceeds the 40 GW landing ceiling, making the landing layer a stress point.

### ⚠️ Label mapping — read this before running

**The code uses `W1/W2/W3`, `L1/L2/L3`, `P1/P2/P3`. The thesis uses `W30/W37.5/W45`, `L_no/L_lim/L_unc`, `P0/P25/P75`.** They map in order:

| Code | Thesis | Meaning |
|---|---|---|
| `wind_dim_W1` | W30 | Σ min = 30.583 GW |
| `wind_dim_W2` | W37.5 | Σ min = 37.583 GW |
| `wind_dim_W3` | W45 | Σ min = 44.583 GW |
| `landing_dim_L1` | L_no | `storage_cap_max: 0` |
| `landing_dim_L2` | L_lim | `storage_cap_max: 0.56` GWh |
| `landing_dim_L3` | L_unc | no cap |
| `premium_dim_P1` | **P0** | 0% premium (costs identical to onshore) |
| `premium_dim_P2` | **P25** | +25% |
| `premium_dim_P3` | **P75** | +75% |



### Reproducing the disabled runs

The 27 offshore-storage-**disabled** runs behind the SQ3 results are not defined as scenarios in this repository. They were produced by **commenting out offshore storage in the YAML and re-running the same 27 scenario names**.

`ES_BESS_offshore` is declared in three places, and **all of the location-level ones must be disabled together**:

| File | Lines | Role |
|---|---|---|
| `techs/storage.yaml` | 23–40 | Tech definition |
| `locs/locations_BL.yaml` | 3722, 3728, 3734, 3740, 3746, 3752 | Assigns the tech to the 6 offshore hubs |
| `scenarios/capacities_BL.yaml` | 10971–11000 | **Re-assigns it to the same 6 hubs** inside the `Scenario_S1_KM` override |
| `scenarios/capacities_BL.yaml` | 11206–11231 | `premium_dim_P1/P2/P3` cost overrides |

> ⚠️ **Commenting out `locations_BL.yaml` alone may not be sufficient.** Every scenario resolves through `Scenario_S1_KM`, whose override block also assigns `ES_BESS_offshore` to all six hubs — and Calliope merges overrides into the location definition. Disable both blocks, and confirm the result as below.
>
> The `premium_dim_*` blocks act at `techs:` level, not `locations:`, so with no offshore loc_techs left they are inert and can be left alone.

**Always verify.** `Runfile_BL_generic.py` writes the fully merged model via `save_commented_model_yaml()` alongside the results — grep that file for `ES_BESS_offshore` to confirm no offshore loc_techs survived. A silently-still-enabled "disabled" run is indistinguishable from a real one except by a near-zero cost difference.



## Repository layout

```
DELFTBLUE_SET/
├── Runfile_BL_generic.py          # Main entry point: takes a scenario name as argv
├── Runfile_BL_KM.py               # Single hard-coded scenario (legacy/debug)
├── calliope_async_patch.py        # LP-critical monkey-patch (see below)
├── scenario_list.txt              # 27 scenario names, read line-by-line by the SLURM array
│
├── Research_Runs/
│   ├── Scenario_BL.yaml           # Top-level model definition: imports, time, run/solver config
│   ├── model_config/
│   │   ├── locs/locations_BL.yaml       # All nodes, coordinates, per-node tech lists, links
│   │   ├── techs/                       # Technology definitions
│   │   │   ├── asset_groups.yaml        #   tech_groups: parents, WACC, cost classes
│   │   │   ├── demand.yaml, supply.yaml, renewables.yaml, powerplants.yaml
│   │   │   ├── storage.yaml             #   ES_BESS_IDES + ES_BESS_offshore
│   │   │   ├── transmission.yaml        #   HVAC, offshore HVDC, artificial carrier links
│   │   │   ├── emissions.yaml           #   ETS budget, CO2 sinks
│   │   │   └── electrolysers.yaml, heat_techs.yaml, reformers.yaml, SMRs*.yaml   [DISABLED]
│   │   └── scenarios/
│   │       ├── capacities_BL.yaml       # Per-node capacity bounds + W/L/P dimension overrides
│   │       ├── scenarios_S1.yaml        # Composes the 27 scenarios from the dimensions
│   │       ├── demand.yaml              # Demand profile overrides per background scenario
│   │       └── emissions.yaml           # ETS discount override [DISABLED]
│   └── timeseries_data/
│       ├── demand/NBNL_KM_2040/         # Node-level demand profiles (KM = Koersvaste Middenweg)
│       ├── renewables/                  # Wind on/offshore + PV capacity factor profiles, 2040
│       └── import_export/               # Cross-border price profiles, 2040
│
├── sh/                            # SLURM submission scripts
│   ├── run_array.sh               #   Main: array job over scenario_list.txt
│   └── ...                        #   Variants exploring time limits, resolutions, clustering
└── KM_RUNS/SH-KM/                 # Legacy SMR-era submission scripts [see Legacy code]
```

### How scenarios compose

`Scenario_BL.yaml` imports everything. A scenario name resolves through two layers:

```
base_run_KM_W3_L1_P1                       # in scenarios_S1.yaml
  ├── capacities_KM_W3_L1_P1               # in capacities_BL.yaml
  │     └── [Scenario_S1_KM, wind_dim_W3, landing_dim_L1, premium_dim_P1]
  └── demand_KM                            # in scenarios/demand.yaml
        └── demand_NBNL_KM_2040 → demand/NBNL_KM_2040/KM_Power_final.csv
```

`KM_Power_final.csv` is electricity demand **with power-to-heat folded in** — PtH is served as electricity rather than as a separate heat carrier.

---

## Running the model

### Prerequisites

- Calliope 0.6.10, Gurobi 12.0.0 (with licence), Python 3.9
- On DelftBlue, a conda environment named `calliope`

### Locally / single scenario

```bash
python Runfile_BL_generic.py base_run_KM_W3_L1_P1
```

Writes two files to `$OUTPUT_ROOT/<scenario>_legacy/`:
- `<name>_<timestamp>.yaml` — the fully merged, commented model definition (useful for verifying that overrides applied as intended)
- `<name>_<timestamp>.nc` — NetCDF results

`OUTPUT_ROOT` is hard-coded to `/scratch/$USER/DELFTBLUE_SET/output/BL` — **change this if you are not on DelftBlue.**

### On DelftBlue (all 27 scenarios)

```bash
sbatch sh/run_array.sh
```

This runs a SLURM array (`--array=1-27%1`, one at a time) reading scenario names line-by-line from `scenario_list.txt`.

> **Note:** `run_array.sh` requests `--cpus-per-task=47` while `Scenario_BL.yaml` sets Gurobi `Threads: 16`. The thesis reports runs at 16 threads / 170 GB RAM. Reconcile these before relying on the resource request.

### The async patch — do not skip this

`calliope_async_patch.py` must be applied **before** building the model (both runfiles call `apply_async_binary_patch()` already).

Calliope 0.6.x adds storage and transmission techs to `loc_techs_asynchronous_prod_con` whenever the key `force_asynchronous_prod_con` is *present*, even when set to `false`. That creates a `prod_con_switch` **binary variable** per loc_tech — silently turning this LP into a MILP that does not solve in available wall-time. The patch keeps techs in the async set only when the flag is actually truthy.

If you see unexpected binaries or a model that never converges, check this patch is applied first.

### Solver configuration

Set in `Scenario_BL.yaml` under `run.solver_options`. Barrier with crossover disabled; `ScaleFlag: 2` mitigates numerical conditioning from the large `bigM`-to-variable ratio.

`BarConvTol` sets the effective optimality criterion. At `1e-4` the objective uncertainty is roughly **2–3 M€/yr per run**, so a paired enabled-vs-disabled cost difference carries **up to ~6 M€/yr of solver noise**. Differences within that band are not attributable to offshore storage.

---

## Key results

- Offshore storage is selected at scale **only when the cost premium is low (≤25%) and offshore wind is high (≥37.5 GW)**. Landing-point storage availability barely matters.
- Allocation ranges from negligible up to **~112 GWh** at W45+P0, collapsing by 80–90% at P25 and to near zero at P75.
- It concentrates at **O-G67 and O-IJL** — the two hubs the model is free to overplant relative to export cable capacity. This is a consequence of cable-sizing freedom, not of the locations themselves; giving all hubs the same freedom spreads the allocation out.
- Where allocation is largest, the system cost saving is **78–79 M€/yr (~0.3% of total system cost)** — robust but modest. It substitutes for onshore storage, cuts offshore wind curtailment, and at 45 GW also displaces export cable expansion and gas dispatch, lowering CO₂ by ~2–2.5%.

**Conclusion:** offshore storage is a *conditional upstream response* whose value comes from co-optimisation with offshore wind overplanting and export cable sizing — not from being a cheaper battery.

---

## Reproducibility status

What this repository does and does not reproduce from the thesis:

| Thesis component | Status |
|---|---|
| 27 enabled scenarios (Ch. 4.2, SQ2) | ✅ Defined in `scenarios_S1.yaml`, runnable via `sh/run_array.sh` |
| 27 disabled counterfactuals (Ch. 4.3, SQ3) | ⚠️ Not defined — produced by manually commenting out offshore storage. See [above](#reproducing-the-disabled-runs) |
| Robustness: battery cost (72 M€/GWh, 8 M€/GW) | ⚠️ Not defined as an override |
| Robustness: weather year 2019 (ENTSO-E ERAA) | ⚠️ Profiles not included in `timeseries_data/` |
| Robustness: relaxed legacy cable bounds (0.1 GW) | ⚠️ Not defined as an override |
| Robustness: +50 €/MWh import uplift | ⚠️ Not defined as an override |
| Post-processing / figures / tables | ➡️ Not here — see the sibling `../Postprocessing/` and `../analysis_results/` folders |

The robustness checks in Chapter 4.4 were run by editing parameters directly, in the same way as the disabled runs. Reproducing them means re-applying those edits by hand from the descriptions in the thesis text.

Since every model variant was produced by editing this checkout in place, **the repository can only ever represent one of the 54+ configurations at a time, and which one is not recorded.** Treat the thesis text as the authoritative description of each variant, and the archived merged YAML written alongside each run's `.nc` as the record of what was actually solved.

> **Solver settings differ from the thesis.** This repository has `BarConvTol: 1e-3` and `SoftMemLimit: 90`; Appendix C.3 reports `1e-4` and `170`. The ~6 M€/yr solver-noise band used to judge significance in Section 4.3.1 is derived from `BarConvTol: 1e-4`, so **set it to `1e-4` before reproducing any cost-difference result.** Also note `sh/run_array.sh` requests 47 CPUs while the solver is configured for 16 threads.

---

## Known limitations

Documented in full in Chapter 5.2 of the thesis. The ones that most affect how you should read model output:

- **3-hourly resolution.** Hourly exceeded available memory on DelftBlue during matrix construction. This smooths short peaks and likely *understates* the upstream peak-shaving role that is offshore storage's distinctive value.
- **LP, not MILP.** A full-year MILP did not complete within the 24h limit available. Integer constraints on transmission directionality and storage operation are relaxed, so export cables are sized continuously (in reality they come in 2 GW HVDC / 700 MW AC blocks) and offshore HVDC links are bidirectional. The reverse-flow diagnostic (thesis D.5.3) shows reverse flow is <1.3% of forward flow, so the relaxation does not materially distort results.
- **kmeans clustering was rejected**, not merely unused. Preliminary 2–3 week tests showed substantial deviation in system cost and storage deployment vs. MILP; full-year LP tracked the MILP tests closely. The clustering options are left commented in `Scenario_BL.yaml` for reproducibility.
- **One weather year, one demand profile, exogenous import prices, perfect foresight.**
- **No land-use, permitting or acceptance costs**, and no ancillary-service value streams. Both omissions likely understate offshore storage's relative value.
- **OCGT dispatch is zero everywhere.** Expected: without ramp constraints the model fully uses more efficient CCGT capacity, and at 3h resolution a CCGT covers any ramp event within one timestep anyway.

---

## Legacy code and provenance

This model is adapted and extended from an existing Calliope model of the Dutch system by **Hasselaar (2026)**, which studied SMR cogeneration under the same NBNL *Koersvaste Middenweg* background. This thesis modified the electricity network and technology representation and added offshore wind hubs, landing points, offshore transmission links, and offshore storage.

The upstream model is kept in this repository as the sibling folder `Calliope_Dutch_Model_KH_ServerCopy`, alongside `Calliope_Model_Original` and the NBNL data-transfer folders. Several YAML files here still carry `COMMENTS KEVIN` headers from that lineage.

Traces of that origin remain and are **inactive**:

- `model.name` is still `Calliope_Dutch_SMR`
- `techs/SMRs.yaml`, `SMRs+50.yaml`, `SMRs-25.yaml`, `heat_techs.yaml`, `electrolysers.yaml`, `reformers.yaml` are present but not imported by `Scenario_BL.yaml`
- Hydrogen, gas and heat demand/storage/transmission are commented out throughout, marked with `STEP 1`–`STEP 6` comments documenting the power-only cleanup
- `KM_RUNS/SH-KM/` and parts of `sh/` contain SMR-era submission scripts (`HI_*`, `HIX_*`, `RR_*`, `RRX_*`, `TO_*`, `TOX_*`) that reference `$HOME/calliope_models`, not this repository's path
- `Runfile_BL_KM.py` hard-codes a single scenario and writes to a relative `output/` path; `Runfile_BL_generic.py` supersedes it

These were kept rather than deleted to preserve traceability of what was disabled. If you fork this for new work, they are safe to remove.

---

## Data sources

| Data | Source |
|---|---|
| Demand, most tech costs, capacity bounds | NBNL Energy Transition Model — *Koersvaste Middenweg* (TenneT, 2025) |
| Weather-dependent profiles (2012) | NBNL/ETM, derived from PECD |
| Offshore wind costs | OESTER project (TNO, 2025) |
| Battery costs | Busch (2024); Rangelova & Jones (2025) |
| Offshore storage premium | TNO (Verstraten & van Dooren, 2025); North Sea Energy (Jepma et al., 2018) |
| Offshore wind hubs, cables, landing points | VAWOZ / PAWOZ / Ontwikkelkader Wind op Zee |
| Onshore grid topology | TenneT netkaarten; Hoogspanningsnet.com |
| Transmission costs | L'Abbate (2022); Härtel et al. (2017) |
| PV lower bounds | PBL (2025) |

---

## Citation

```bibtex
@mastersthesis{vantienhoven2026offshore,
  author  = {van Tienhoven, Marijn},
  title   = {System Conditions for Offshore Electricity Storage:
             A system-level assessment of cost-effectiveness and system impacts
             in a high offshore wind Dutch power system},
  school  = {Delft University of Technology},
  year    = {2026},
  type    = {MSc thesis},
  address = {Delft, The Netherlands}
}
```

## Acknowledgements

Written in collaboration with **RWE** within the **OESTER** project, carried out with a Top Sector Energy subsidy from the Ministry of Economic Affairs and Climate Policy, implemented by the Netherlands Enterprise Agency (RVO), MOOI subsidy round 2024.

Computational resources provided by the **Delft High Performance Computing Centre** (DelftBlue).

Built on [Calliope](https://calliope.readthedocs.io/) (Pfenninger & Pickering, 2018).
