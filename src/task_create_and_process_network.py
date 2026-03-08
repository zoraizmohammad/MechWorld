# Meant for use with Hoffman2 Cluster batch submissions
# Estimated runtimes: 0.5-hr for 100 DSU, 1-hr for 200 DSU, 3-hr for 300 DSU, 6-hr for 400 DSU
# Example cli: 
# python src\task_create_and_process_network.py 100 0.7 0.72 results\sandbox 1 1 --write_dumps --write_restarts
import os
import argparse
from datetime import datetime as dt
from assemble_pg_network import generate_pg_network, process_distribution_string
from run_lammps_isotropic_strain import run_isotropic_prestrain_minimize

parser = argparse.ArgumentParser()
parser.add_argument("size")
parser.add_argument("rho")
parser.add_argument("anisotropy")
parser.add_argument("output_directory")
parser.add_argument("sge_job_id")
parser.add_argument("sge_task_id")
parser.add_argument("--write_images",   action='store_true')
parser.add_argument("--write_dumps",    action='store_true')
parser.add_argument("--write_restarts", action='store_true')
parser.add_argument("--dist", default="FS-2-30-0.9")
args = parser.parse_args()

# Required
if args.size and args.rho and args.anisotropy and args.output_directory and args.sge_job_id and args.sge_task_id:
    size = int(args.size);
    rho_gap = float(args.rho);
    anisotropy = float(args.anisotropy);
    outdir = args.output_directory;
    id1 = args.sge_job_id;
    id2 = args.sge_task_id;

# Optional/Flags
write_images   = args.write_images;
write_dumps    = args.write_dumps;
write_restarts = args.write_restarts;
distrib_str    = args.dist;

distribution = process_distribution_string(distrib_str, size)

os.makedirs(outdir, exist_ok=True)

filename = os.path.join(f"{outdir}",f"job{id1}.{id2}_dsu{size}_rho{int(rho_gap*100)}_a{int(anisotropy*100)}.network")

(_, _, _, _, _, _) = generate_pg_network(size, rho_gap, anisotropy, distribution, filename, False)

# Standard list of outputs
if write_dumps:
    std_dump_criteria = [
        ("INITIAL", None,  None ),
        ("FORCE",   0.13,  None ),
        ("FINAL",   None,  None ),
        ];
else:
    std_dump_criteria = None;

if write_restarts:
    std_restart_criteria = [
        ("ALL"    , 0.00, 0.30),
        ];
else:
    std_restart_criteria = None;

run_isotropic_prestrain_minimize(
    filename, 
    max_strain           = 0.3,
    number_strain_steps  = None, 
    write_debug_images   = write_images, 
    dump_specs           = std_dump_criteria, 
    restart_specs        = std_restart_criteria,
    remap                = True)