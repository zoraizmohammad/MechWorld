from os import makedirs
import pandas as pd
import matplotlib.pyplot as plt
from ensemble_isotropic_strain import *

### START OF PROGRAM FOR TESTING
# Settings
working_dirpath = os.path.join(os.path.curdir,"isostrain_Jan13");
isotropic_parameters = [0.33, 0.72, 1.0];
number_networks_per_group = 8;

# Subfunction to create folder if it not found
makedirs(working_dirpath, exist_ok=True)

# Loop to create networks
create_networks_in_groups_with_varying_isotropic_parameter(working_dirpath, 200, 1.0, isotropic_parameters, number_networks_per_group, False)

network_regex = r".*\.network$";
run_networks_nve(working_dirpath, network_regex, False)

lst_output_regex : list[str] = list()
lst_label : list[str] = list()

for a in isotropic_parameters:
    lst_output_regex.append(r'.*_a'+str(int(a*100))+r'\.out')
    lst_label.append(r"$\chi$ = " + str(a))

lst_colorname = ['black','red','blue','purple'];

#Plot Stress vs. Strain...
for i in range(0,len(lst_output_regex)):
    output_regex = lst_output_regex[i]
    colorname = lst_colorname[i]
    labelstr = lst_label[i]
    dfs = collect_list_of_dataframes(working_dirpath,output_regex)
    stress_dfs = list()
    for file_df in dfs:
        stress_dfs.append(calc_stress_df_from_file_df(file_df));

    if len(stress_dfs) == 0:
        continue;
    else:
        combined_stress_df = pd.concat(stress_dfs)

    add_stress_curve(combined_stress_df, colorname, labelstr);

finish_stress_curve()

# Plot Stress Ratio vs. Strain...
for i in range(0,len(lst_output_regex)):
    output_regex = lst_output_regex[i]
    colorname = lst_colorname[i]
    labelstr = lst_label[i]
    dfs = collect_list_of_dataframes(working_dirpath,output_regex)
    stress_dfs = list()
    for file_df in dfs:
        stress_dfs.append(calc_stress_df_from_file_df(file_df));
    
    if len(stress_dfs) == 0:
        continue;
    else:
        combined_stress_df = pd.concat(stress_dfs)

    add_stress_ratio_curve(combined_stress_df, colorname, labelstr);

finish_stress_ratio_curve()

# Plot Energy vs. Strain...
dfs = collect_list_of_dataframes(working_dirpath,r'.*\.out');
energy_dfs = list()
for file_df in dfs:
    energy_dfs.append(calc_energy_df_from_file_df(file_df));

combined_energy_df = pd.concat(energy_dfs)
print(combined_energy_df)
add_energy_curves(combined_energy_df, "black", "combined");
finish_energy_curve();