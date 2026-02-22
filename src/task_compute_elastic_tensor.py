import argparse
import shutil
from run_lammps_elastic_tensor import lammps_calculate_elastic_tensor

a = argparse.ArgumentParser()
a.add_argument("filepath")
a.parse_args();

if a.filepath:
    filepath = a.filepath

success_bool = lammps_calculate_elastic_tensor(filepath)

if success_bool:
    shutil.rmtree(filepath);