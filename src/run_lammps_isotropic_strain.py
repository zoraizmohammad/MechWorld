from lammps import lammps
from simulation_constants_settings import GLYCAN_COEFFICIENTS, PEPTIDE_COEFFICIENTS, RUNITER, INITIAL_MINIMIZATION_ITERATIONS
from os.path import splitext
# https://docs.lammps.org/Python_module.html

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
    L.command("units nano")
    L.command("dimension 2")
    L.command("atom_style angle")
    L.command("boundary p p p")

    #### 2) System definition
    L.command(f"read_data {network_filepath}")
    L.command(f"variable print_filename string \"{filepath_no_extension}.out\"")

    #### 3) Pair/Bond/Angle Settings
    L.command(f"variable up equal {max_strain}")
    L.command("variable prescribed_strain equal 1 + ${up}")

    # Set pair_style, required for bonds
    L.command("pair_style zero 5") # zero = no interactions, distance to consider neighbors
    L.command("pair_coeff * *")    # These non-existant pairs should exist between all types of atoms

    # Extension Components
    L.command(f"bond_style hybrid harmonic nonlinear")
    L.command(f"bond_coeff 1 harmonic {GLYCAN_COEFFICIENTS[0]} {GLYCAN_COEFFICIENTS[1]}")
    L.command(f"bond_coeff 2 nonlinear {PEPTIDE_COEFFICIENTS[0]} {PEPTIDE_COEFFICIENTS[1]} {PEPTIDE_COEFFICIENTS[2]}")

    # Bending Component :: https://docs.lammps.org/angle_harmonic.html
    L.command("angle_style hybrid harmonic")
    L.command("angle_coeff 1 harmonic 4.18E-2 180.0") # btype, K (E/rad^2), theta0 (deg). Note: K is placeholder from slides

    #### 4) Monitoring
    L.command("thermo 1")
    L.command("thermo_style custom step temp pe press pxx pyy pxy lx ly vol")
    L.command("thermo_modify norm no")

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
    L.command(f"variable miniter equal {str(INITIAL_MINIMIZATION_ITERATIONS)}")  # !!! X minimization iterations before and after the deformation is applied (changed from 3E3 -> 5E3, need more?)

    ### 5) Minimize the energy before any deformation is applied
    L.command("minimize 1.0e-6 1.0e-6 ${miniter} 10000")

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
    L.command("minimize 1.0e-6 1.0e-6 ${miniter} 10000")

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

def run_isotropic_prestrain_minimize(network_filepath : str, max_strain : float, number_strain_steps : int | None, output_images : bool = False, output_dump_of_atoms_bonds : bool = False, remap : bool = False) -> list[str]:

    # This is the scaling factor that needs to
    # scaling_factor = (1+max_strain)**(1/number_strain_steps)

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
        # Step size of 2 DSU broke down after a boundary size of 247 DSU (last good energy was ~64) without remaps, might want to do dynamic steps?

    dx_step = -1*(xlo*max_strain)/number_strain_steps;
    dy_step = -1*(ylo*max_strain)/number_strain_steps;
    
    L = lammps();

    filepath_no_extension = splitext(network_filepath)[0]
    
    #### 1) Simulation Settings
    L.command("units nano")
    L.command("dimension 2")
    L.command("atom_style angle")
    L.command("boundary p p p")

    #### 2) System definition
    L.command(f"read_data {network_filepath}")
    L.command(f"variable print_filename string \"{filepath_no_extension}.out\"")

    #### 3) Pair/Bond/Angle Settings
    L.command(f"variable up equal {max_strain}")
    L.command("variable prescribed_strain equal 1 + ${up}")

    # Set pair_style, required for bonds
    L.command("pair_style zero 5") # zero = no interactions, distance to consider neighbors
    L.command("pair_coeff * *")    # These non-existant pairs should exist between all types of atoms

    # Extension Components
    L.command(f"bond_style hybrid harmonic nonlinear")
    L.command(f"bond_coeff 1 harmonic {GLYCAN_COEFFICIENTS[0]} {GLYCAN_COEFFICIENTS[1]}")
    L.command(f"bond_coeff 2 nonlinear {PEPTIDE_COEFFICIENTS[0]} {PEPTIDE_COEFFICIENTS[1]} {PEPTIDE_COEFFICIENTS[2]}")

    # Bending Component :: https://docs.lammps.org/angle_harmonic.html
    L.command("angle_style hybrid harmonic")
    L.command("angle_coeff 1 harmonic 4.18E-2 180.0") # btype, K (E/rad^2), theta0 (deg). Note: K is placeholder from slides

    #### 4) Monitoring
    L.command("thermo 1")
    L.command("thermo_style custom step temp pe press pxx pyy pxy lx ly vol")
    L.command("thermo_modify norm no")

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

    L.command(f"variable miniter equal {str(INITIAL_MINIMIZATION_ITERATIONS)}")  # !!! X minimization iterations before and after the deformation is applied (changed from 3E3 -> 5E3, need more?)

    ### 5) Minimize the energy before any deformation is applied
    L.command("minimize 1.0e-6 1.0e-6 ${miniter} 10000")

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
    L.command("print \"step temp pe press pxx pyy pxy lx ly vol glycan_pe angle_pe peptide_pe\" file ${print_filename}");
    L.command("print \"${p_step} ${p_temp} ${p_pe} ${p_press} ${p_pxx} ${p_pyy} ${p_pxy} ${p_lx} ${p_ly} ${p_vol} ${glycan_pe} ${angle_pe} ${peptide_pe}\" append ${print_filename}")

    ### 6) Take a series of discrete box deformation steps, minimizing the energy after each, then output parameters

    for i in range(0,number_strain_steps):
        #L.command(f"change_box all x scale {scaling_factor} y scale {scaling_factor} remap");
        if remap:
            L.command(f"change_box all x delta {-1*dx_step} {dx_step} y delta {-1*dy_step} {dy_step} remap");
        else:
            L.command(f"change_box all x delta {-1*dx_step} {dx_step} y delta {-1*dy_step} {dy_step}");
        
        L.command("minimize 1.0e-6 1.0e-6 ${miniter} 10000")
        L.command("run 0")
        L.command("print \"${p_step} ${p_temp} ${p_pe} ${p_press} ${p_pxx} ${p_pyy} ${p_pxy} ${p_lx} ${p_ly} ${p_vol} ${glycan_pe} ${angle_pe} ${peptide_pe}\" append ${print_filename}")

    # At this point, we've reached the final state. Output screenshots and dumps if necessary.
    if output_images:
        L.command(f"write_dump all image {splitext(network_filepath)[0]}.final.jpg type type bond type type atom no")

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