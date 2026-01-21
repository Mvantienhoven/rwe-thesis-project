
import pyomo.environ as pyo
import pandas as pd

# import plotly.express as px

def process_system_balance_duals(system_balance_duals):
    column=system_balance_duals[0]

    info = column.str.split("[(::)]")
    info = pd.DataFrame(info.tolist(), index= info.index)
    info.drop([0,2,5],axis=1,inplace=True)
    
    car_and_time = info[3].str.split(",")
    info[['car','time']] = pd.DataFrame(car_and_time.tolist(), index= info.index)
    info.drop([3,4],axis=1,inplace=True)
    info.columns = ['region','carrier','timesteps']
    info.region = pd.DataFrame(info.region.str.split("[']").to_list(), index=info.index)[1]
    info.carrier = pd.DataFrame(info.carrier.str.split("[']").to_list(), index=info.index)[0]
    info.timesteps = pd.DataFrame(info.timesteps.str.split("[']").to_list(), index=info.index)[1]
    info.timesteps = info.timesteps + ':00:00'
    info.timesteps = pd.to_datetime(info.timesteps)
    info['shadowprice'] = system_balance_duals[1]

    return (info)


def toggle_duals_on(model,flag):
    if flag:
        print ("Toggling duals ON")
        model._backend_model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
    else:
        print ("Toggling duals OFF")
    
    
def postprocess_shadowprices(model,flag):
    if flag:
        
        duals = {} 
        for c in model._backend_model.component_objects(pyo.Constraint, active=True):
            duals[("{} Constraint".format(c))] = []
            for index in c:
                duals["{} Constraint".format(c)].append(("{}".format(index), model._backend_model.dual[c[index]]))
            duals["{} Constraint".format(c)] = pd.DataFrame(duals["{} Constraint".format(c)])

        system_balance_duals = duals['system_balance_constraint Constraint']
        container = process_system_balance_duals(system_balance_duals)
        container.set_index('timesteps',inplace=True)
    
    else:
        container = pd.merge(model.results.timesteps.to_dataframe(), model.results.loc_carriers.to_dataframe(),how='cross')
        container[['region','carrier']] = container['loc_carriers'].str.split('::',expand=True)
        # container.rename(columns={'timesteps':'timestep'}, inplace=True)
        container['shadowprice'] = 0
    
    return container


# def save_shadowprices(duals, scenario, dir):
#     # if duals is not None and duals != 0:
#     try:
#         fig = px.line(duals.groupby(['timestep','carrier']).mean().reset_index(), x='timestep', y='dual-value',color='carrier')
#     except:
#         try:
#             fig = px.line(duals.groupby(['timesteps','carrier']).mean().reset_index(), x='timesteps', y='dual-value',color='carrier')
#         except:
#             print ("not plotting duals")
#             raise 
#         else:
#             if scenario == None:
#                 fig.write_html(ncdir+'/duals_'+time+'_'+case+'_base.html')
#             else:
#                 fig.write_html(ncdir+'/duals_'+time+'_'+case+'_'+scenario+'.html')
        
#         raise 

#     else:
#         if scenario == None:
#             fig.write_html(ncdir+'/duals_'+time+'_'+case+'_base.html')
#         else:
#             fig.write_html(ncdir+'/duals_'+time+'_'+case+'_'+scenario+'.html')
    
#     return fig