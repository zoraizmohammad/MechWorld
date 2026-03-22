from lammps import lammps
from simulation_constants_settings import *
from os.path import splitext
from typing import Union;
import numpy as np;
# https://docs.lammps.org/Python_module.html

def lammps_PG_simulation_settings(L : lammps):
    L.command("units nano")
    L.command("dimension 2")
    L.command("atom_style angle")
    L.command("boundary p p p")

def lammps_PG_potential_settings(L : lammps):
    #### 3) Pair/Bond/Angle Settings
    # Set pair_style, required for bonds
    L.command("pair_style zero 5") # zero = no interactions, distance to consider neighbors
    L.command("pair_coeff * *")    # These non-existant pairs should exist between all types of atoms

    # Extension Components
    L.command(f"bond_style hybrid harmonic nonlinear")
    L.command(f"bond_coeff 1 harmonic {GLYCAN_COEFFICIENTS[0]} {GLYCAN_COEFFICIENTS[1]}")
    L.command(f"bond_coeff 2 nonlinear {PEPTIDE_COEFFICIENTS[0]} {PEPTIDE_COEFFICIENTS[1]} {PEPTIDE_COEFFICIENTS[2]}")

    # Bending Component :: https://docs.lammps.org/angle_harmonic.html
    L.command("angle_style hybrid harmonic")
    L.command(f"angle_coeff 1 harmonic {ANGLE_COEFFICIENTS[0]} {ANGLE_COEFFICIENTS[1]}")

def lammps_PG_thermo_settings(L : lammps):
    L.command("thermo 1")
    L.command("thermo_style custom step temp pe press pxx pyy pxy lx ly vol")
    L.command("thermo_modify norm no")

def read_starting_dimensions(network_filepath : str) -> tuple[float, float]:
    # Assumes that the box is centered so -1 * xlo = xhi, etc. 

    xlo = None;
    ylo = None;

    with open(network_filepath, 'r') as f:

        contents = f.readlines()
        for i, line in enumerate(contents):
            line = line.strip()
            if line.endswith("xhi"):
                xlo = float(line.split()[0]);
            elif line.endswith("yhi"):
                ylo = float(line.split()[0]);
                break;
            elif line == "Masses" or line == "Atoms" or i > 100:
                raise ValueError(f"Could not find xlo and xhi in {network_filepath}");

    return (xlo, ylo);

def run_isotropic_prestrain_nve(network_filepath : str, max_strain : float, output_images : bool = False, output_dump_of_atoms_bonds : bool = False) -> list[str]:
    
    L = lammps();

    filepath_no_extension = splitext(network_filepath)[0]
    
    #### 1) Simulation Settings
    lammps_PG_simulation_settings(L)
    L.command(f"variable up equal {max_strain}")
    L.command("variable prescribed_strain equal 1 + ${up}")

    #### 2) System definition
    L.command(f"read_data {network_filepath}")
    L.command(f"variable print_filename string \"{filepath_no_extension}.out\"")

    #### 3) Pair/Bond/Angle Settings
    lammps_PG_potential_settings(L)

    #### 4) Monitoring
    lammps_PG_thermo_settings(L)

    #### 4) Monitoring
    # Tempory variables so we can print these quantities
    L.command("variable p_step   equal step") # variables need to be defined for printing values
    L.command("variable p_temp   equal temp")
    L.command("variable p_pe     equal pe")
    L.command("variable p_press  equal press")
    L.command("variable p_pxx    equal pxx")
    L.command("variable p_pyy    equal pyy")
    L.command("variable p_pxy    equal pxy")
    L.command("variable p_lx     equal lx")
    L.command("variable p_ly     equal ly")
    L.command("variable p_vol    equal vol")

    L.command(f"variable runiter equal {str(RUNITER)}") # !!! Deformation is applied over X propagation steps
    L.command(f"variable etol equal {str(ENERGY_TOLERANCE)}")
    L.command(f"variable ftol equal {str(FORCE_TOLERANCE)}")
    L.command(f"variable maxeval equal {str(MINIMIZATION_MAX_EVALUATIONS)}")
    L.command(f"variable maxiter equal {str(MINIMIZATION_MAX_ITERATIONS)}")

    ### 5) Minimize the energy before any deformation is applied
    L.command("minimize ${etol} ${ftol} ${maxiter} ${maxeval}")

    if output_images:
        L.command(f"write_dump all image {filepath_no_extension}.relaxed.jpg type type bond type type atom no")

    if output_dump_of_atoms_bonds:
        L.command("compute b1 all property/local btype batom1 batom2")
        L.command("compute b2 all bond/local dist fx fy fz")
        L.command("run 0")
        L.command(f"write_dump all local {filepath_no_extension}.relaxed.bonds index c_b1[1] c_b1[2] c_b1[3] c_b2[1] c_b2[2] c_b2[3] c_b2[4]")
        L.command(f"write_dump all custom {filepath_no_extension}.relaxed.atoms id mol type x y")
        L.command("uncompute b1")
        L.command("uncompute b2")

    #https://docs.lammps.org/compute_bond.html
    L.command("compute bondE  all bond")
    L.command("compute angleE all angle")
    L.command('variable glycan_pe  equal "c_bondE[1]"')
    L.command('variable angle_pe   equal "c_angleE[1]"')
    L.command('variable peptide_pe equal "c_bondE[2]"')

    # Write minimized quantities
    L.command("run 0")
    #print "${glycan_pe} ${angle_pe} ${peptide_pe}"
    L.command("print \"step temp pe press pxx pyy pxy lx ly vol glycan_pe angle_pe peptide_pe\" file ${print_filename}");
    L.command("print \"${p_step} ${p_temp} ${p_pe} ${p_press} ${p_pxx} ${p_pyy} ${p_pxy} ${p_lx} ${p_ly} ${p_vol} ${glycan_pe} ${angle_pe} ${peptide_pe}\" append ${print_filename}")

    ### 6) Prescribe strain, let positions and velocities update

    # Deformation specification
    L.command("fix 1 all nve"); # Forces from bonds will result in motion
    L.command("fix 2 all deform 1 x scale ${prescribed_strain} y scale ${prescribed_strain} units box remap none")

    # Discrete timestep outputs
    L.command("fix 3 all print 500 \"${p_step} ${p_temp} ${p_pe} ${p_press} ${p_pxx} ${p_pyy} ${p_pxy} ${p_lx} ${p_ly} ${p_vol} ${glycan_pe} ${angle_pe} ${peptide_pe}\" append ${print_filename}")
    L.command("run ${runiter}")

    ### 7) Minimize energy of deformed state
    L.command("minimize ${etol} ${ftol} ${maxiter} ${maxeval}")

    if output_images:
        L.command(f"write_dump all image {splitext(network_filepath)[0]}.final.jpg type type bond type type atom no")

    # write down final stress, strain, energy fraction
    L.command("print \"${p_step} ${p_temp} ${p_pe} ${p_press} ${p_pxx} ${p_pyy} ${p_pxy} ${p_lx} ${p_ly} ${p_vol} ${glycan_pe} ${angle_pe} ${peptide_pe}\" append ${print_filename}")

    if output_dump_of_atoms_bonds:
        L.command("compute b1 all property/local btype batom1 batom2")
        L.command("compute b2 all bond/local dist fx fy fz")
        L.command("run 0")
        L.command(f"write_dump all local {filepath_no_extension}.final.bonds index c_b1[1] c_b1[2] c_b1[3] c_b2[1] c_b2[2] c_b2[3] c_b2[4]")
        L.command(f"write_dump all custom {filepath_no_extension}.final.atoms id mol type x y")
        L.command("uncompute b1")
        L.command("uncompute b2")

    L.close();

    return filepath_no_extension + ".out";

# Specification for outputs: list[tuple[str,float,float]]
# ("INITIAL",None,None)
# ("FINAL",None,None)
# ("ALL" ,{MIN},{MAX})
# ("ONCE",{MIN},{MAX})
# ("PRESCRIBE",{EXACT},None) TODO
# (None,None,None)

def to_write_or_not_to_write(output_specifications : Union[list[tuple[str,float,float], None]], cur_strain : float, is_final_step : bool):
    # That is the question

    assert (type(output_specifications) == list) or (output_specifications == None)

    if (output_specifications == None):
        return False;

    # Remove all elements that have been suppressed in previous calls
    filtered_specifications = list();
    for spec_tuple in output_specifications:
        if (spec_tuple != None) and (spec_tuple != (None, None, None)):
            filtered_specifications.append(spec_tuple);
    output_specifications = filtered_specifications;

    if (len(output_specifications) == 0):
        return False;

    # Look at the criteria one by one
    for spec in output_specifications:
        assert (type(spec) == tuple) or (type(spec) == None)
        # Indicates that this criteria has been fulfilled, no longer needed
        if spec[0] == None:
            continue

        if (spec[0] == "INITIAL") and (cur_strain == 0):
            spec = (None, None, None); # Suppress, skip in future
            return True
        elif (spec[0] == "FINAL") and (is_final_step):
            return True
        elif (spec[0] == "ALL") and (spec[1] <= cur_strain) and (cur_strain <= spec[2]):
            return True;
        elif (spec[0] == "ONCE") and (spec[1] <= cur_strain) and (cur_strain <= spec[2]):
            spec = (None, None, None); # Suppress, skip in future
            return True;

        # If the maximum strain has been passed, we don't need to eval because strain is monotonically increasing
        if ((spec[0] == "ALL") or (spec[0] == "ONCE")) and (cur_strain > spec[2]):
            spec = (None, None, None); # Suppress, skip in future
            continue;

    return False;

def insert_forced_strain_criteria(
        output_specifications : Union[list[tuple[str,float,float], None]], 
        stepwise_strains : np.ndarray
        ):
    
    if output_specifications == None:
        return output_specifications, stepwise_strains;

    for i,criteria in enumerate(output_specifications):
        print(criteria)
        if criteria[0] == "FORCE":
            # Add this strain to the list, maintain monotonically increasing
            prescribed_strain : float = criteria[1];
            idx = len(stepwise_strains[stepwise_strains <= prescribed_strain]);

            if prescribed_strain == stepwise_strains[idx]:
                # Another criteria has added this strain, so we don't add it again
                output_specifications[i] = ("ONCE", prescribed_strain - 1E-6, prescribed_strain + 1E-6);
                continue;

            stepwise_strains = np.insert(stepwise_strains, idx, prescribed_strain)

            # Change criteria to generate ou
            output_specifications[i] = ("ONCE", prescribed_strain - 1E-6, prescribed_strain + 1E-6);

    return output_specifications, stepwise_strains

def run_isotropic_prestrain_minimize(
        network_filepath : str, 
        max_strain : float, 
        number_strain_steps : Union[int, None], 
        write_debug_images : bool = False, 
        dump_specs : list[tuple[str,float,float]] = None,
        restart_specs : list[tuple[str,float,float]] = None,
        remap : bool = True) -> list[str]:

    # Inputs
    assert type(remap) == bool;
    assert (type(dump_specs) == list)    or (dump_specs == None);
    assert (type(restart_specs) == list) or (restart_specs == None);

    # Calculate number of steps, then get box length at each step
    (xlo, ylo) = read_starting_dimensions(network_filepath)

    if number_strain_steps == None:
        if remap:
            maximum_length_increase_per_step = 2; # DSU
        else:
            maximum_length_increase_per_step = 1; # DSU
            
        total_length_increase = 2*max_strain*max(abs(xlo), abs(ylo));
        number_strain_steps = int(total_length_increase / maximum_length_increase_per_step) + 1;
        number_strain_steps = max(30, number_strain_steps); # Minimum of 30 steps even for smaller patches
        print(f"----- DEBUG ----- :: {number_strain_steps}")

    # Automatically-generated steps
    stepwise_xlo_values = np.linspace(xlo, xlo*(1+max_strain), number_strain_steps)
    stepwise_ylo_values = np.linspace(ylo, ylo*(1+max_strain), number_strain_steps)

    stepwise_strains = np.linspace(0,max_strain,number_strain_steps+1)

    _, stepwise_strains = insert_forced_strain_criteria(dump_specs   , stepwise_strains)
    _, stepwise_strains = insert_forced_strain_criteria(restart_specs, stepwise_strains)

    stepwise_xlo_values = xlo * (stepwise_strains + 1);
    stepwise_ylo_values = ylo * (stepwise_strains + 1);
    
    L = lammps();

    filepath_no_extension = splitext(network_filepath)[0];
    
    #### 1) Simulation Settings
    lammps_PG_simulation_settings(L)
    L.command(f"variable up equal {max_strain}")
    L.command("variable prescribed_strain equal 1 + ${up}")

    #### 2) System definition
    L.command(f"read_data {network_filepath}")
    L.command(f"variable print_filename string \"{filepath_no_extension}.out\"")

    #### 3) Pair/Bond/Angle Settings
    lammps_PG_potential_settings(L)

    #### 4) Monitoring
    lammps_PG_thermo_settings(L)

    # Tempory variables so we can print these quantities
    L.command("variable p_step   equal step") # variables need to be defined for printing values
    L.command("variable p_temp   equal temp")
    L.command("variable p_pe     equal pe")
    L.command("variable p_press  equal press")
    L.command("variable p_pxx    equal pxx")
    L.command("variable p_pyy    equal pyy")
    L.command("variable p_pxy    equal pxy")
    L.command("variable p_lx     equal lx")
    L.command("variable p_ly     equal ly")
    L.command("variable p_vol    equal vol")

    L.command(f"variable etol equal {str(ENERGY_TOLERANCE)}")
    L.command(f"variable ftol equal {str(FORCE_TOLERANCE)}")
    L.command(f"variable maxiter equal {str(MINIMIZATION_MAX_ITERATIONS)}")
    L.command(f"variable maxeval equal {str(MINIMIZATION_MAX_EVALUATIONS)}")

    ### 5) Minimize the energy before any deformation is applied
    L.command("minimize ${etol} ${ftol} ${maxiter} ${maxeval}")

    if write_debug_images:
        L.command(f"write_dump all image {filepath_no_extension}.relaxed.jpg type type bond type 1.5 atom no zoom 1.8")

    #https://docs.lammps.org/compute_bond.html
    L.command("compute bondE  all bond")
    L.command("compute angleE all angle")
    L.command('variable glycan_pe  equal "c_bondE[1]"')
    L.command('variable angle_pe   equal "c_angleE[1]"')
    L.command('variable peptide_pe equal "c_bondE[2]"')

    ### 6) Take a series of discrete box deformation steps, minimizing the energy after each, then output parameters

    L.command("print \"step temp pe press pxx pyy pxy lx ly vol glycan_pe angle_pe peptide_pe\" file ${print_filename}");
    for i in range(0,number_strain_steps):
        cur_xlo = stepwise_xlo_values[i];
        cur_ylo = stepwise_ylo_values[i];
        cur_strain = (cur_xlo / stepwise_xlo_values[0]) - 1;
        is_final_step : bool = (i == number_strain_steps-1);

        if remap:
            L.command(f"change_box all x final {cur_xlo} {-1*cur_xlo} y final {cur_ylo} {-1*cur_ylo} remap");
        else:
            L.command(f"change_box all x final {cur_xlo} {-1*cur_xlo} y final {cur_ylo} {-1*cur_ylo}");
        
        L.command("minimize ${etol} ${ftol} ${maxiter} ${maxeval}");
        L.command("run 0");

        # Always write thermodynamic information to the .out file
        L.command("print \"${p_step} ${p_temp} ${p_pe} ${p_press} ${p_pxx} ${p_pyy} ${p_pxy} ${p_lx} ${p_ly} ${p_vol} ${glycan_pe} ${angle_pe} ${peptide_pe}\" append ${print_filename}");

        # Only write dumps if requested in dump_specs
        OUTPUT_NAME_ROUND_PRECISION = 3;

        if to_write_or_not_to_write(dump_specs, cur_strain, is_final_step):
            L.command("compute b1 all property/local btype batom1 batom2")
            L.command("compute b2 all bond/local dist fx fy fz")
            L.command("run 0")
            L.command(f"write_dump all local {filepath_no_extension}_prestr{round(cur_strain,OUTPUT_NAME_ROUND_PRECISION)}.bonds index c_b1[1] c_b1[2] c_b1[3] c_b2[1] c_b2[2] c_b2[3] c_b2[4]")
            L.command(f"write_dump all custom {filepath_no_extension}_prestr{round(cur_strain,OUTPUT_NAME_ROUND_PRECISION)}.atoms id mol type x y")
            L.command("uncompute b1")
            L.command("uncompute b2")
        
        # Only write restarts if requested in restarts_specs
        if to_write_or_not_to_write(restart_specs, cur_strain, is_final_step):
            L.command(f"write_restart {filepath_no_extension}_prestr{round(cur_strain,OUTPUT_NAME_ROUND_PRECISION)}.restart");

    # At this point, we've reached the final state. Output screenshots and dumps if necessary.
    if write_debug_images:
        L.command(f"write_dump all image {splitext(network_filepath)[0]}.final.jpg type type bond type 1.5 atom no zoom 1.8")

    L.close();

    return filepath_no_extension + ".out";