# NOTE: This script should not need to be
# modified. See in.elastic for more info.
#
# Find which reference length to use

if "${dir} == 1" then &
   "variable len0 equal ${lx0}" 
if "${dir} == 2" then &
   "variable len0 equal ${ly0}" 
if "${dir} == 3" then &
   "variable len0 equal ${ly0}"

# Reset box and simulation parameters

clear
box tilt large
read_restart restart.equil
include PG_2D_potential.mod

variable runiter equal 50000

# Negative deformation

variable delta equal -${up}*${len0}
variable deltaxy equal -${up}*xy

fix 1 all nve

if "${dir} == 1" then &
   "fix 2 all deform 10 x delta 0 ${delta} units box remap none"
if "${dir} == 2" then &
   "fix 2 all deform 10 y delta 0 ${delta} units box remap none"
if "${dir} == 3" then &
   "fix 2 all deform 10 xy delta ${delta} units box remap none"

run ${runiter}

# Relax atoms positions

minimize ${etol} ${ftol} ${maxiter} ${maxeval}
write_dump all image dump.post.negative.${dir}.jpg type type

# Obtain new stress tensor
 
variable tmp equal pxx
variable pxx1 equal ${tmp}
variable tmp equal pyy
variable pyy1 equal ${tmp}
variable tmp equal pxy
variable pxy1 equal ${tmp}

# Compute elastic constant from pressure tensor

variable C1neg equal ${d1}
variable C2neg equal ${d2}
variable C3neg equal ${d3}

# Reset box and simulation parameters

clear
box tilt large
read_restart restart.equil
include PG_2D_potential.mod

# Positive deformation

variable delta equal ${up}*${len0}
variable deltaxy equal ${up}*xy

fix 1 all nve

if "${dir} == 1" then &
   "fix 2 all deform 10 x delta 0 ${delta} units box remap none"
if "${dir} == 2" then &
   "fix 2 all deform 10 y delta 0 ${delta} units box remap none"
if "${dir} == 3" then &
   "fix 2 all deform 10 xy delta ${delta} units box remap none"

run ${runiter}

# Relax atoms positions

minimize ${etol} ${ftol} ${maxiter} ${maxeval}
write_dump all image dump.post.positive.${dir}.jpg type type

# Obtain new stress tensor
 
variable tmp equal pxx
variable pxx1 equal ${tmp}
variable tmp equal pyy
variable pyy1 equal ${tmp}
variable tmp equal pxy
variable pxy1 equal ${tmp}

# Compute elastic constant from pressure tensor

variable C1pos equal ${d1}
variable C2pos equal ${d2}
variable C3pos equal ${d3}

# Combine positive and negative 

variable C1${dir} equal 0.5*(${C1neg}+${C1pos})
variable C2${dir} equal 0.5*(${C2neg}+${C2pos})
variable C3${dir} equal 0.5*(${C3neg}+${C3pos})

# Delete dir to make sure it is not reused

variable dir delete
