# NOTE: This script can be modified for different atomic structures, 
# units, etc. See in.elastic for more info.
#

# Define the finite deformation size. Try several values of this
# variable to verify that results do not depend on it.
variable up equal 0.01
 
# Define the amount of random jiggle for atoms
# This prevents atoms from staying on saddle points
# variable atomjiggle equal 1

# Uncomment one of these blocks, depending on what units
# you are using in LAMMPS and for output

# metal units, elastic constants in eV/A^3
#units		metal
#variable cfac equal 6.2414e-7
#variable cunits string eV/A^3

# metal units, elastic constants in GPa
#units		metal
#variable cfac equal 1.0e-4
#variable cunits string GPa

# real units, elastic constants in GPa
#units		real
#variable cfac equal 1.01325e-4
#variable cunits string GPa

# nano units, elastic constants in GPa
units nano
variable cfac equal 1.01325e-8 # 1 attogram/(nanometer-nanosecond^2) = E9 Pa = E4 Bars
variable cunits string GPa

# Define minimization parameters
variable etol equal 1.0e-8 
variable ftol equal 1.0e-8
variable maxiter equal 10000
variable maxeval equal 10000
variable dmax equal 1.0e-2

# Generate the box and atom positions using an input file
dimension 2
atom_style angle
boundary p p p
read_data file.data

