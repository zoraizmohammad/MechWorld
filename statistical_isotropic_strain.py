# Imports
from assemble_pg_network import generate_pg_network
import os.path
from os import makedirs, listdir
import re

from run_lammps_isotropic_strain import run_isotropic_prestrain

from process_isotropic_prestrain import ThermoStruct, import_isotropic_prestrain_data

# Simple Helper Functions
def create_networks_in_groups_with_varying_isotropic_parameter(working_directory, isotropic_parameters, networks_per_group):
    for group_index, alpha in enumerate(isotropic_parameters):
        for network_index in range(0,networks_per_group):
            filename = os.path.join(f"{working_directory}",f"g{group_index}_n{network_index}_a{int(alpha*100)}.network")
            (density_fraction, crosslink_ratio, lst_atoms, lst_bonds, lst_angle) = generate_pg_network(200, 0.5, alpha, filename)

def run_networks(dirpath, regex_pattern, rerun):
    network_filenames_to_run = list();
    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            expected_output_file = os.path.join(dirpath,os.path.splitext(filename)[0] + ".out")
            if rerun or not os.path.exists(expected_output_file):
                print(f"Running {filename}...")
                file_to_run = os.path.join(dirpath,filename)
                run_isotropic_prestrain(file_to_run, 0.3, False)
            else:
                print(f"Skipped {filename} : existing output file was found")
                continue;

def generate_energy_vs_elastic(dirpath, regex_pattern):
    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            expected_output_file = os.path.join(dirpath,os.path.splitext(filename)[0] + ".out")
            if rerun or not os.path.exists(expected_output_file):
                print(f"Running {filename}...")
                file_to_run = os.path.join(dirpath,filename)
                run_isotropic_prestrain(file_to_run, 0.3, False)
            else:
                print(f"Skipped {filename} : existing output file was found")
                continue;

# Settings
working_dirname = os.path.join(os.path.curdir,"isostrain1");
isotropic_parameters = [0.30, 0.50, 0.80, 1.0];
number_networks_per_group = 3;

# Subfunction to create folder if it not found
makedirs(working_dirname, exist_ok=True)

# Loop to create networks
create_networks_in_groups_with_varying_isotropic_parameter(working_dirname, isotropic_parameters, number_networks_per_group)

#filenames = "";

#PG_filepath = os.path.join(os.path.curdir,"isostrain1","g4_n4.network")

#run_isotropic_prestrain(PG_filepath,0.3,True)

network_regex = r".*\.network$";

run_networks(working_dirname, network_regex, False)

# Loop to run lammps isotropic prestrain on all files with a specific regex

