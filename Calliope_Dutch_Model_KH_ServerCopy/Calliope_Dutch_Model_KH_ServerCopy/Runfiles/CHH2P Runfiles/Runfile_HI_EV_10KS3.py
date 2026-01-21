import os
import calliope
from datetime import datetime
from pathlib import Path
import logging
from pathlib import Path
import pandas as pd

base_dir = Path.cwd()  
MODEL_FILE = base_dir / "Research_Runs" / "Scenario_HI_10KS3_CHH2P.yaml"
OUTPUT_DIR = base_dir / "output"    / "2.Scenario_S1"
LOG_VERBOSITY = "INFO" 
SCENARIOS = ["base_run_EV"]

def create_versioned_filename(base_name, extension, output_dir=OUTPUT_DIR):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"{base_name}_{timestamp}.{extension}"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir / filename

tech_list =  ["pp_SMR_Hitachi_CHH2P_1","pp_SMR_Hitachi_CHH2P_2","pp_SMR_RollsRoyce_CHH2P_1","pp_SMR_RollsRoyce_CHH2P_2",
              "pp_SMR_Thorizon_CHH2P_1","pp_SMR_Thorizon_CHH2P_2","pp_SMR_Hitachi_CHH2P_3","pp_SMR_RollsRoyce_CHH2P_3", "pp_SMR_Thorizon_CHH2P_3"]


##FOR UNITS
from pyomo.environ import Var, Constraint, NonNegativeReals

def inject_trapezoid_constraints(model, tech_list, tol=1e-6):
    """
    Adds convex‐combination trapezoid constraints for each technology in tech_list.
    
    Parameters
    ----------
    model : calliope.Model
        The initialized Calliope model (after build_only=True).
    tech_list : list of str
        Technology identifiers (e.g., ["SMR_CHH2P1", "SMR_CHH2P2", "SMR_CHH2P3"]).
    tol : float
        Tolerance to allow minor numerical slack.
    """
    bm = model.backend._backend

    for cname in [
        "balance_conversion_plus_primary_constraint",
        "balance_conversion_plus_out_2_constraint",
        "balance_conversion_plus_out_3_constraint",
    ]:
        if not hasattr(bm, cname):
            continue
        con = getattr(bm, cname)
        for idx in con.index_set():
            loc_tech = idx[0] if cname.endswith("primary_constraint") else idx[1]
            loc, tech = loc_tech.split("::")
            if tech in tech_list:
                con[idx].deactivate()
   
    # 1. Define weight variables for all loc_techs & timesteps
    bm.w_a = Var(bm.loc_techs, bm.timesteps, domain=NonNegativeReals)
    bm.w_b = Var(bm.loc_techs, bm.timesteps, domain=NonNegativeReals)
    bm.w_c = Var(bm.loc_techs, bm.timesteps, domain=NonNegativeReals)
    bm.w_d = Var(bm.loc_techs, bm.timesteps, domain=NonNegativeReals)

    # 2. Sum‐to‐one (≤1) constraint
    def sum_to_units_rule(m, loc_tech, t):
        loc, tech = loc_tech.split("::")
        if tech not in tech_list:
            return Constraint.Skip
        return (m.w_a[loc_tech, t] + m.w_b[loc_tech, t] + 
                m.w_c[loc_tech, t] + m.w_d[loc_tech, t]) <= m.units[loc_tech] + tol
    
    bm.sum_to_units = Constraint(bm.loc_techs, bm.timesteps, rule=sum_to_units_rule)

    # 3. Dispatch‐link constraints for each carrier
    def make_link_rule(carrier, corner_factors):
        """
        Returns a rule function linking carrier_prod to sum(w_i * factor_i) * cap.
        
        carrier : str
            "Electricity", "Hydrogen", or "Heat"
        corner_factors : tuple of floats
            (factor_a, factor_b, factor_c, factor_d) for this carrier
        """
        def link_rule(m, loc_tech, t):
            loc, tech = loc_tech.split("::")
            if tech not in tech_list:
                return Constraint.Skip
            cap = m.energy_cap_per_unit[loc_tech]
            prod = m.carrier_prod[(f"{loc}::{tech}::{carrier}", t)]
            fa, fb, fc, fd = corner_factors
            return prod == cap * (
                fa * m.w_a[loc_tech, t]
              + fb * m.w_b[loc_tech, t]
              + fc * m.w_c[loc_tech, t]
              + fd * m.w_d[loc_tech, t])
        return link_rule

    # Corner factor definitions for P, H2, T
    eps = 1e-3
    P_factors  = (eps, 0.54, 0.90, eps)
    H2_factors = (0.192, 0.03, 0.03, 0.30)
    T_factors  = (0.8511, 0.8511, 0.0, 0.0)

    bm.link_P  = Constraint(bm.loc_techs, bm.timesteps, rule=make_link_rule("electricity", P_factors))
    bm.link_H2 = Constraint(bm.loc_techs, bm.timesteps, rule=make_link_rule("hydrogen",  H2_factors))
    bm.link_T  = Constraint(bm.loc_techs, bm.timesteps, rule=make_link_rule("heat",       T_factors))


if __name__ == "__main__":
    calliope.set_log_verbosity(LOG_VERBOSITY, include_solver_output=True)
    
    scenario_string = ",".join(SCENARIOS)
    print(f"\n{'='*50}")
    print(f"RUNNING MODEL")
    print(f"Scenarios: {scenario_string}")
    print(f"{'='*50}\n")
    
    model = calliope.Model(str(MODEL_FILE), scenario=scenario_string)
    model.run(build_only=True)

    inject_trapezoid_constraints(model, tech_list, tol=1e-6)
    
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


    yaml_file = create_versioned_filename("HI_10KS3_CHH2P" + scenario_string, "yaml")
    model.save_commented_model_yaml(yaml_file)
    print(f" Fully merged model YAML saved to {yaml_file}")

    results = model.backend.rerun()

    nc_file = create_versioned_filename("HI_10KS3_CHH2P" + scenario_string, "nc")
    results.to_netcdf(str(nc_file))
    print(f" Model run completed. Results saved to {nc_file}")
    print("\nModel run completed successfully!")

