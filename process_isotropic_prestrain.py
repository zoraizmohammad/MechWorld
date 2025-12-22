from dataclasses import dataclass
from simulation_constants_settings import *;
import numpy as np;
import matplotlib.pyplot as plt;

@dataclass
class ThermoStruct:
    step : int; 
    temp : float;
    pe : float;
    press : float;
    pxx : float;
    pyy : float;
    pxy : float;
    lx : float;
    ly : float;
    vol : float;
    glycan_pe : float;
    angle_pe : float;
    peptide_pe : float;

def import_isotropic_prestrain_data(filename : str) -> list[ThermoStruct]:

    # Break into lines
    with open(filename,"r") as f:
        lines = [line.strip() for line in f]

    i = 0; # 1st Line
    verify = "step temp pe press pxx pyy pxy lx ly vol glycan_pe angle_pe peptide_pe";
    if not lines[i].startswith(verify):
        raise ValueError(f"Expected at line {i+1}: {verify}");

    lst_structs : list[ThermoStruct] = list();

    for i in range(1,len(lines)):
        if lines[i].startswith("#"): # ignore
            continue;
        
        data = lines[i].split();

        struct = ThermoStruct(
            step   = int(data[0]),
            temp   = float(data[1]),
            pe     = float(data[2]),
            press  = float(data[3]),
            pxx    = float(data[4]),
            pyy    = float(data[5]),
            pxy    = float(data[6]),
            lx     = float(data[7]),
            ly     = float(data[8]),
            vol    = float(data[9]),
            glycan_pe  = float(data[10]),
            angle_pe   = float(data[11]),
            peptide_pe = float(data[12])
        );

        lst_structs.append(struct);

    return lst_structs

def get_stress_vs_deformation(filename : str):
    lst_snaps = import_isotropic_prestrain_data(filename)

    deformation_array = np.zeros(len(lst_snaps));
    stress_xx_array   = np.zeros(len(lst_snaps));
    stress_yy_array   = np.zeros(len(lst_snaps));

    relaxed = lst_snaps[0];
    for i, snap in enumerate(lst_snaps):
        deformation_array[i] = (snap.lx - relaxed.lx)/(relaxed.lx);
        stress_xx_array[i]   = -(snap.pxx - relaxed.pxx);
        stress_yy_array[i]   = -(snap.pyy - relaxed.pyy);

    return deformation_array, stress_xx_array, stress_yy_array;

def compare_isotropy_levels():


    deformation_low, stress_xx_low, stress_yy_low = get_stress_vs_deformation("isoprestrain_33.data");
    deformation_medium, stress_xx_medium, stress_yy_medium = get_stress_vs_deformation("isoprestrain_72.data");
    deformation_high, stress_xx_high, stress_yy_high = get_stress_vs_deformation("isoprestrain_100.data");

    fig, ax = plt.subplots(1)
    ax.set_title("Non-Linear Stress-Strain Relationships")
    ax.set_xlabel("Deformation")
    ax.set_ylabel("Stress [N/m]")
    # https://docs.lammps.org/compute_pressure.html
    # Normally, pressure = attogram/(nanometer-nanosecond^2), but because of units in 2D, it is N/m form
    long1 = ax.plot(deformation_low, stress_xx_low, linestyle="--", color="black")
    circ1 = ax.plot(deformation_low, stress_yy_low, color="black")
    long2 = ax.plot(deformation_medium, stress_xx_medium, linestyle="--", color="red")
    circ2 = ax.plot(deformation_medium, stress_yy_medium, color="red")
    long3 = ax.plot(deformation_high, stress_xx_high, linestyle="--", color="blue")
    circ3 = ax.plot(deformation_high, stress_yy_high, color="blue")
    ax.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.show()

    fig, ax = plt.subplots(1)
    ax.plot(deformation_low, stress_xx_low/stress_yy_low,       color="black");
    ax.plot(deformation_low, stress_xx_medium/stress_yy_medium, color="red");
    ax.plot(deformation_low, stress_xx_high/stress_yy_high,     color="blue");
    plt.show()

compare_isotropy_levels()

