# Meant for use with Hoffman2 Cluster batch submissions
# Estimated runtimes: 0.5-hr for 100 DSU, 1-hr for 200 DSU, 3-hr for 300 DSU, 6-hr for 400 DSU
# Example cli: python src\create_and_process_single_network.py 200 1.0 0.72 C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\results
# Linux: ~/
import os
import platform
import argparse
from datetime import datetime as dt
from assemble_pg_network import generate_pg_network
from run_lammps_isotropic_strain import run_isotropic_prestrain_minimize

parser = argparse.ArgumentParser()
parser.add_argument("size")
parser.add_argument("rho")
parser.add_argument("alpha")
parser.add_argument("output_directory")
parser.add_argument("sge_job_id")
parser.add_argument("sge_task_id")
args = parser.parse_args()

if args.size and args.rho and args.alpha and args.output_directory and args.sge_job_id and args.sge_task_id:
    size = int(args.size);
    rho_gap = float(args.rho);
    alpha = float(args.alpha);
    outdir = args.output_directory;
    id1 = args.sge_job_id;
    id2 = args.sge_task_id;

# SGE job and task id? add

# Create directory if needed
os.makedirs(outdir, exist_ok=True)

# Get info for filenames
#now = dt.now();
#timestr = now.strftime("%Y-%m-%d-%H-%M-%S")
#hostname = platform.node()

filename = os.path.join(f"{outdir}",f"job{id1}.{id2}_dsu{size}_rho{int(rho_gap*100)}_a{int(alpha*100)}.network")

# Create Network
(density_fraction, crosslink_ratio, _, _, _, _) = generate_pg_network(size, rho_gap, alpha, filename)

# Run the Network
run_isotropic_prestrain_minimize(filename, 0.3, None, output_images=True, output_dump_of_atoms_bonds=True, remap=True)