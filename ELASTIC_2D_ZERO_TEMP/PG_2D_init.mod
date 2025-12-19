# NOTE: This script can be modified for different atomic structures, 
# units, etc. See in.elastic for more info.

# Define the finite deformation size. Try several values of this
# variable to verify that results do not depend on it.

variable up equal 1.0e-1
#variable up equal 1.0e-2  # E1 = 9.14425848948698e-12 GPa 

#variable up equal 1.0e-3  # E1 = 1.74123962690091e-10 GPa
#variable up equal 1.0e-4  # E1 = 8.555654487917e-11 GPa
# variable up equal 1.0e-5
# Combined Remap: E1 = 8.24260265410084e-11 GPa
# Combines Extensional: E1 = 3.73299787434679e-08 GPa

units nano


# real units, elastic constants in GPa
#units		real
#variable cfac equal 1.01325e-4
#variable cunits string GPa

# nano units, elastic constants in GPa
units nano
variable cfac equal 1.01325e-8 # 1 attogram/(nanometer-nanosecond^2) = E9 Pa = E4 Bars
variable cunits string GPa

# Define minimization parameters
variable etol equal 0.0 
variable ftol equal 1.0e-10
variable maxiter equal 10000
variable maxeval equal 1000
variable dmax equal 1.0e-2

# Initial Atoms
dimension 2
atom_style angle
boundary p p p
read_data network1.data
