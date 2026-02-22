import argparse
import shutil
from run_lammps_elastic_tensor import lammps_calculate_elastic_tensor

parser = argparse.ArgumentParser()
parser.add_argument("filepath")
args = parser.parse_args();

if args.filepath:
    filepath = args.filepath

success_bool = lammps_calculate_elastic_tensor(filepath)

if success_bool:
    shutil.rmtree(filepath);