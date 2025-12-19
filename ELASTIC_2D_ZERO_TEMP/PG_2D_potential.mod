# NOTE: This script can be modified for different pair styles 
# See in.elastic for more info.

# Set pair_style, required for bonds
pair_style zero 5 # zero = no interactions, distance to consider neighbors
pair_coeff * *    # This non-existant pairs should exist between all types

# Extension Components
bond_style hybrid harmonic nonlinear
bond_coeff 1 harmonic 5.570 2.00              # Nguyen 2015
bond_coeff 2 nonlinear 0.1709 0.9065 4.0878   # Curve fit to WLC in Nguyen 2015

neigh_modify delay 0 every 1 check yes

# Bending Component :: https://docs.lammps.org/angle_harmonic.html
angle_style harmonic
angle_coeff 1 4.18E-2 180.0

# Setup output
thermo		1
thermo_style custom step temp pe press pxx pyy pxy lx ly vol
thermo_modify norm no
