# Meant for use with Hoffman2 Cluster batch submissions
# Estimated runtimes: 0.5-hr for 100 DSU, 1-hr for 200 DSU, 3-hr for 300 DSU, 6-hr for 400 DSU
# Example cli: python src\create_and_process_single_network.py 200 1.0 0.72 results-dir/
import os
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
parser.add_argument("--write_images",   action='store_true')
parser.add_argument("--write_dumps",    action='store_true')
parser.add_argument("--write_restarts", action='store_true')
args = parser.parse_args()

if args.size and args.rho and args.alpha and args.output_directory and args.sge_job_id and args.sge_task_id:
    size = int(args.size);
    rho_gap = float(args.rho);
    alpha = float(args.alpha);
    outdir = args.output_directory;
    id1 = args.sge_job_id;
    id2 = args.sge_task_id;
    write_images   = args.write_images;
    write_dumps    = args.write_dumps;
    write_restarts = args.write_restarts;

os.makedirs(outdir, exist_ok=True)

filename = os.path.join(f"{outdir}",f"job{id1}.{id2}_dsu{size}_rho{int(rho_gap*100)}_a{int(alpha*100)}.network")

(_, _, _, _, _, _) = generate_pg_network(size, rho_gap, alpha, filename)

run_isotropic_prestrain_minimize(filename, 0.3, None, write_images, write_dumps, True, write_restarts)