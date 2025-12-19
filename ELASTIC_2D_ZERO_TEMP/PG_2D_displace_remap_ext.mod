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

# Positive deformation

variable delta equal ${up}*${len0}
variable deltaxy equal ${up}*xy

if "${dir} == 1" then &
   "change_box all x delta 0 ${delta} xy delta ${deltaxy} remap units box"
if "${dir} == 2" then &
   "change_box all y delta 0 ${delta} remap units box"
if "${dir} == 3" then &
   "change_box all xy delta ${delta} remap units box"

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

variable C1${dir} equal ${C1pos}
variable C2${dir} equal ${C2pos}
variable C3${dir} equal ${C3pos}

# Delete dir to make sure it is not reused

variable dir delete
