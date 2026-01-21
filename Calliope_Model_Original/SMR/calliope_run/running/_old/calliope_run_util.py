
import os
import pyomo.environ as pyo
import pandas as pd
# import plotly.express as px
import sys

import calliope as cp

pd.options.mode.chained_assignment = None  # default='warn'

from calliope_customize_shadowprices import toggle_duals_on, postprocess_shadowprices
from calliope_customize_constraints import toggle_custom_constraints

def check_termination_condition(model):
    
    termination = model._model_data.attrs.get("termination_condition", "did_not_yet_run")
    if termination not in ["optimal", "did_not_yet_run", "feasible"]:
        cp.exceptions.BackendError("Problem is non optimal, not saving anything.")
        
        print("Model termination condition was not optimal!! Exiting")
        sys.exit()

            
def runmodel(model, scenario=None, custom_constraints=False, shadowprices=True):

    # model.run(build_only=True)
    
    
    if custom_constraints or shadowprices:
        
        # Build model
        model.run(build_only=True)

        # Add constraints or access to dual variables
        toggle_custom_constraints(model, scenario, custom_constraints)
        toggle_duals_on(model,shadowprices)
        
        # Rerun the model with new constraint.
        run_model = model.backend.rerun()
    
    else:
        run_model = model.run()
            
    print("***************\nFinished model \n" + model.info() + "\n" + str(model.results.attrs['scenario']) + "\n***************")
    
    check_termination_condition(model)

    balance_duals = postprocess_shadowprices(model,shadowprices)


    return (model, balance_duals)


def create_directory(folder):
    
    # Check if directory exists, otherwise create it.
    ispath = os.path.isdir(folder)
    if not ispath:
        print(f"Directory {folder} not found, making one.")
        os.mkdir(folder)
    else:
        print(f"Directory {folder} already exists.")