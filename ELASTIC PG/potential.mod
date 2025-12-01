# NOTE: This script can be modified for different pair styles 
# See in.elastic for more info.

# Choose potential
pair_style zero 5
pair_coeff * *

### Define behavior of the bonds in the datafile

# Stretching Component
bond_style hybrid harmonic nonlinear
#Bond Parameters with gylcan are from Nguyen 2015, Peptide Model is Curve Fit
bond_coeff 1 harmonic 5.570 2.00
bond_coeff 2 nonlinear 0.162340253242252 1.0 3.615948499717430

# Bending Component :: https://docs.lammps.org/angle_harmonic.html
angle_style harmonic
angle_coeff 1 4.18E-2 180.0 # btype, K (E/rad^2), theta0 (deg). Note: K is placeholder from slides

# Setup neighbor style
# neighbor 5.0 nsq
# neigh_modify once no every 1 delay 0 check yes

# Setup minimization style
min_style	     cg
min_modify	     dmax ${dmax} line quadratic

# Setup output
thermo		1
thermo_style custom step temp pe press pxx pyy pzz pxy pxz pyz lx ly lz vol
thermo_modify norm no