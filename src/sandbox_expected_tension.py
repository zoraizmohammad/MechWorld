from units import u_ATM_to_PASCAL
import numpy as np

mean_Pt_ATM = 0.8;
var_Pt_ATM = 0.1;

mean_D_um = 0.70;
var_D_um = 0.05;

turgor_pressure_Pa = np.array([mean_Pt_ATM-var_Pt_ATM, mean_Pt_ATM+var_Pt_ATM]) * u_ATM_to_PASCAL # atm -> Pa N/m2
#turgor_pressure_Pa = np.array([0.28, 0.32]) * u_ATM_to_PASCAL # atm -> Pa N/m2
diameter_um = np.array([mean_D_um-var_D_um,mean_D_um+var_D_um])
radius_m = (diameter_um/2) * 1E-6 # D is 0.25 - 1.0 um https://en.wikipedia.org/wiki/Escherichia_coli
t = 6 * 1E-9 # m

# Lower Bound
tension_yy : tuple[float,float] = (turgor_pressure_Pa[0]*radius_m[0],   turgor_pressure_Pa[1]*radius_m[1]);   # [N/m]
tension_xx : tuple[float,float] = (turgor_pressure_Pa[0]*radius_m[0]/2, turgor_pressure_Pa[1]*radius_m[1]/2); # [N/m]