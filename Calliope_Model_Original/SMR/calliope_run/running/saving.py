
import pandas as pd


pd.options.mode.chained_assignment = None  # default='warn'


def savemodel_netcdf(run_model, folder):

    # Save output to netCDF in output folder.
    # This is not always possible, for example when timestep is not equally spaced.
    try:
        run_model.to_netcdf(folder+'/optimal.nc')
    except Exception as e:
        print ("NETCDF FILE COULD NOT BE PRODUCED")            
        print (e)
    
def savemodel_csv(run_model, duals, folder):       
    
    # Save output to CSVs in `case_tag` folder.
    run_model.to_csv(folder)

    # Save duals to CSVs in `case_tag` folder.
    duals.to_csv(folder+'/results_balance_duals.csv')


def saveplot_summary(run_model, folder, mapbox_access_token=None):
    
    try:
        run_model.plot.summary(to_file= folder+'/summary.html', mapbox_access_token=mapbox_access_token)
    except Exception as e:
        print ("SUMMARY PLOT COULD NOT BE PRODUCED")
        print (e)
        
    # Plot summary of Calliope output using built-in function.


def concat_frames(solved_models,kpis):

    df = pd.DataFrame() # carrier con

    for i,model in enumerate(solved_models):

        if i == 0:
            df = model.results['carrier_con'].to_dataframe().groupby(['loc_tech_carriers_con']).sum()
            df['scenarios'] = model.results.attrs['scenario']
        else:
            df_temp = model.results['carrier_con'].to_dataframe().groupby(['loc_tech_carriers_con']).sum()
            df_temp['scenarios'] = model.results.attrs['scenario']
            df = pd.concat([df,df_temp])
            
    return df
