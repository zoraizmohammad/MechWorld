from simulation_constants_settings import *
import numpy as np

tension_yy_SI = np.array([0.0272,0.0172]) # N/m, FS 090
#tension_yy_SI = np.array([0.053149,0.036684]) # N/m, FS 093
diameter_um = np.array([0.60,0.90])
radius_m = (diameter_um/2) * 1E-6 # D is 0.25 - 1.0 um https://en.wikipedia.org/wiki/Escherichia_coli
t = 6 * 1E-9 # m

P = tension_yy_SI / (radius_m*u_ATM_to_PASCAL)
print(P)