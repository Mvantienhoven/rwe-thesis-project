import os
import calliope
from datetime import datetime
from pathlib import Path
import logging
from pathlib import Path
import pandas as pd

base_dir = Path.cwd()  
MODEL_FILE = base_dir / "Research_Runs" / "Scenario_HI_H2.yaml"
OUTPUT_DIR = base_dir / "output"    / "Hitachi"
LOG_VERBOSITY = "INFO" 
SCENARIOS = ["base_run_EV"]

def create_versioned_filename(base_name, extension, output_dir=OUTPUT_DIR):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"{base_name}_{timestamp}.{extension}"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir / filename

tech_list =  ["pp_SMR_Hitachi_CHP_1"]


from pyomo.environ import Var, Constraint, Binary, NonNegativeReals

def inject_chp_segment_switch(model, tech_list, tol=1e-4):
    """
    Enforce (P,T) either = (0,0) if z=0, or on line segment a->b if z=1:
    a=(0.6383*cap,0.8511*cap), b=(1.0*cap,0).
    Here “cap” is the per‐unit capacity (energy_cap_per_unit) already on bm.
    """
    bm = model.backend._backend

    # 1. Deactivate built-in conversion constraints for these techs
    for cname in [
        "balance_conversion_plus_primary_constraint",
        "balance_conversion_plus_out_2_constraint",
    ]:
        if hasattr(bm, cname):
            con = getattr(bm, cname)
            for idx in con.index_set():
                lt = idx[0] if cname.endswith("primary_constraint") else idx[1]
                if lt.split("::")[1] in tech_list:
                    con[idx].deactivate()

    # 2. Binary on/off switch z_lt_t ∈ {0,1}
    bm.z = Var(bm.loc_techs, bm.timesteps, domain=Binary)

    # 3. Segment weights wa, wb ≥ 0
    bm.wa = Var(bm.loc_techs, bm.timesteps, domain=NonNegativeReals)
    bm.wb = Var(bm.loc_techs, bm.timesteps, domain=NonNegativeReals)

    # 4. wa + wb = z
    def sum_to_z(m, lt, t):
        loc, tech = lt.split("::")
        if tech not in tech_list:
            return Constraint.Skip
        return m.wa[lt, t] + m.wb[lt, t] == m.z[lt, t]
    bm.sum_to_z = Constraint(bm.loc_techs, bm.timesteps, rule=sum_to_z)

    # 5. Link Electricity: P = 0.6383*cap*wa + 1.0*cap*wb
    def link_P(m, lt, t):
        loc, tech = lt.split("::")
        if tech not in tech_list:
            return Constraint.Skip
        # per-unit capacity provided by Calliope on the backend
        cap = m.energy_cap_per_unit[lt]
        P = m.carrier_prod[(f"{loc}::{tech}::electricity", t)]
        return P == cap*(0.6383*m.wa[lt, t] + 1.0*m.wb[lt, t])
    bm.link_P = Constraint(bm.loc_techs, bm.timesteps, rule=link_P)

    # 6. Link Heat: T = 0.8511*cap*wa + 0*cap*wb
    def link_T(m, lt, t):
        loc, tech = lt.split("::")
        if tech not in tech_list:
            return Constraint.Skip
        cap = m.energy_cap_per_unit[lt]
        T = m.carrier_prod[(f"{loc}::{tech}::heat", t)]
        return T == cap*(0.8511*m.wa[lt, t] + 0.0*m.wb[lt, t])
    bm.link_T = Constraint(bm.loc_techs, bm.timesteps, rule=link_T)

    # 7. Link dispatch to investment decisions
    def prevent_dispatch_without_units(m, lt, t):
        loc, tech = lt.split("::")
        if tech not in tech_list:
            return Constraint.Skip
        
        # Can only dispatch (z=1) if units are actually purchased
        return m.z[lt, t] <= m.units[lt]

    bm.prevent_dispatch = Constraint(bm.loc_techs, bm.timesteps, 
                                    rule=prevent_dispatch_without_units)

if __name__ == "__main__":
    calliope.set_log_verbosity(LOG_VERBOSITY, include_solver_output=True)
    
    scenario_string = ",".join(SCENARIOS)
    print(f"\n{'='*50}")
    print(f"RUNNING MODEL")
    print(f"Scenarios: {scenario_string}")
    print(f"{'='*50}\n")
    
    model = calliope.Model(str(MODEL_FILE), scenario=scenario_string)
    model.run(build_only=True)

    inject_chp_segment_switch(model, tech_list, tol=1e-4)
    #DIAGNOSTIC: find any empty energy_eff_per_distance entries [TO DEAL WITH PYOMO BUG]
    bm = model.backend._backend
    missing = []
    for idx in bm.energy_eff_per_distance.index_set():
        try:
            val = bm.energy_eff_per_distance[idx]
        except KeyError:
            missing.append(idx)
    if missing:
        print("⚠️ Missing energy_eff_per_distance for these indices (showing up to 10):")
        for i in missing[:10]:
            print(f"  {i}")
        print(f"... and {len(missing) - min(len(missing),10)} more.")
    else:
        print("✅ All energy_eff_per_distance entries populated.")


    yaml_file = create_versioned_filename("HI_H2" + scenario_string, "yaml")
    model.save_commented_model_yaml(yaml_file)
    print(f" Fully merged model YAML saved to {yaml_file}")

    results = model.backend.rerun()

    nc_file = create_versioned_filename("HI_H2" + scenario_string, "nc")
    results.to_netcdf(str(nc_file))
    print(f" Model run completed. Results saved to {nc_file}")
    print("\nModel run completed successfully!")

