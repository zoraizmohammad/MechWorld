from lammps import lammps
import re
from os.path import exists, splitext, dirname, join
from simulation_constants_settings import *
from run_lammps_isotropic_strain import lammps_PG_simulation_settings, lammps_PG_potential_settings, lammps_PG_thermo_settings

def lammps_PG_displacement(L : lammps, filepath_restart, dir):
    # Considering positive displacement only

    L.command(f"variable dir equal {dir}");

    ### Positive Displacement
    L.command("clear");
    L.command("box tilt large");
    L.command(f"read_restart {filepath_restart}");
    lammps_PG_potential_settings(L);
    lammps_PG_thermo_settings(L);

    # Now the file is loaded and configured, apply deformation
    L.commands_list(cmdlist=[
        # Determine reference length
        "if \"${dir} == 1\" then &",
        "\"variable len0 equal ${lx0}\"", 
        "if \"${dir} == 2\" then &",
        "\"variable len0 equal ${ly0}\"", 
        "if \"${dir} == 3\" then &",
        "\"variable len0 equal ${ly0}\"",

        # Deformation
        "variable delta equal ${up}*${len0}",
        "variable deltaxy equal ${up}*xy",

        "if \"${dir} == 1\" then &",
        "\"change_box all x delta 0 ${delta} xy delta ${deltaxy} remap units box\"",
        "if \"${dir} == 2\" then &",
        "\"change_box all y delta 0 ${delta} remap units box\"",
        "if \"${dir} == 3\" then &",
        "\"change_box all xy delta ${delta} remap units box\"",

        # Relax atoms positions
        "minimize ${etol} ${ftol} ${maxiter} ${maxeval}",
        "write_dump all image dump.post.positive.${dir}.jpg type type",

        # Obtain new stress tensor
        "variable tmp equal pxx",
        "variable pxx1 equal ${tmp}",
        "variable tmp equal pyy",
        "variable pyy1 equal ${tmp}",
        "variable tmp equal pxy",
        "variable pxy1 equal ${tmp}",

        # Compute elastic constant from pressure tensor
        "variable C1pos equal ${d1}",
        "variable C2pos equal ${d2}",
        "variable C3pos equal ${d3}",
    ])

    L.commands_list(cmdlist=[
        "variable C1${dir} equal ${C1pos}",
        "variable C2${dir} equal ${C2pos}",
        "variable C3${dir} equal ${C3pos}"
    ])

    # Delete dir to make sure it is not reused
    L.command("variable dir delete");

def lammps_calculate_elastic_tensor(filepath_restart : str) -> bool:
    # Extract basis information about the restart from the filename:
    # https://regex101.com/
    re_prestrain = r".+_prestr(\d\.\d+)"
    prestrain = re.match(re_prestrain, filepath_restart);

    if not exists(filepath_restart):
        raise FileExistsError(f"File could not be found: {filepath_restart}");

    if prestrain == None:
        raise ValueError(f"Strain could not be found in filename: {filepath_restart}");
    else:
        prestrain = prestrain.group(1); # i.e. 0.1
    
    coefficients_filepath = splitext(filepath_restart)[0] + ".elastic_constants"

    #### LAMMPS SCRIPT
    L = lammps();

    #### 1) Simulation Settings
    lammps_PG_simulation_settings(L)
    L.command("variable cfac equal 1.0"); # 1 attogram/(nanometer-nanosecond^2) == 1 MPa
    L.command("variable cunits string MPa");
    L.command(f"variable prestrain equal {prestrain}")
    L.command(f"variable up equal 1E-3")

    L.command(f"variable etol equal {str(MODULI_ENERGY_TOLERANCE)}")
    L.command(f"variable ftol equal {str(MODULI_FORCE_TOLERANCE)}")
    L.command(f"variable maxiter equal {str(MODULI_MINIMIZATION_MAX_ITERATIONS)}")
    L.command(f"variable maxeval equal {str(MODULI_MINIMIZATION_MAX_EVALUATIONS)}")

    #### 2) System definition
    L.command(f"read_restart {filepath_restart}")
    L.command(f"variable print_filename string \"{coefficients_filepath}\"")

    #### 3) Pair/Bond/Angle Settings
    lammps_PG_potential_settings(L)

    #### 4) Monitoring
    L.command("thermo 1")
    L.command("thermo_style custom step temp pe press pxx pyy pxy lx ly vol")
    L.command("thermo_modify norm no")

    #### INITIAL STATE
    # 1) rerun minimization to ensure tolerances are met
    # 2) record pressure & box dimensions
    L.command("minimize ${etol} ${ftol} ${maxiter} ${maxeval}")

    L.command("variable tmp equal pxx")
    L.command("variable pxx0 equal ${tmp}")
    L.command("variable tmp equal pyy")
    L.command("variable pyy0 equal ${tmp}")
    L.command("variable tmp equal pxy")
    L.command("variable pxy0 equal ${tmp}")

    L.command("variable tmp equal lx")
    L.command("variable lx0 equal ${tmp}")
    L.command("variable tmp equal ly")
    L.command("variable ly0 equal ${tmp}")
    L.command("variable tmp equal lz")
    L.command("variable lz0 equal ${tmp}")

    # d1, d2, d3 are finite difference method representations of C1X, C2X, C3X. X is "dir", passed to function.
    # sigma = [C]*epsilon
    # UNITS / DIMENSIONAL ANALYSIS # https://docs.lammps.org/units.html
    # p1 - p0 => attogram/(nanometer-nanosecond^2) == E-21 kg / (E-9 m * E-18 s**2) == E6 Pa == 1 MPa
    # delta / len0 = a.u.

    L.command("variable d1 equal -(v_pxx1-${pxx0})/(v_delta/v_len0)*${cfac}");
    L.command("variable d2 equal -(v_pyy1-${pyy0})/(v_delta/v_len0)*${cfac}");
    L.command("variable d3 equal -(v_pxy1-${pxy0})/(v_delta/v_len0)*${cfac}");

    #### DEFORM: +/- uxx
    lammps_PG_displacement(L, filepath_restart, 1)

    #### DEFORM: +/- uyy
    lammps_PG_displacement(L, filepath_restart, 2)

    #### DEFORM: +/- uxy
    lammps_PG_displacement(L, filepath_restart, 3)

    # Average symmetric components to get final values...
    L.command("variable C11all equal ${C11}");
    L.command("variable C22all equal ${C22}");
    L.command("variable C33all equal ${C33}");

    L.command("variable C12all equal 0.5*(${C12}+${C21})");
    L.command("variable C13all equal 0.5*(${C13}+${C31})");
    L.command("variable C23all equal 0.5*(${C23}+${C32})");

    # Write coefficients to file
    L.command("print \"${prestrain} ${C11all} ${C22all} ${C33all} ${C12all} ${C13all} ${C23all} ${cunits}\" file ${print_filename}")

    return True;