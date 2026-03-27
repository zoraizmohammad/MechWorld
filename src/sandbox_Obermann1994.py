import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gamma, lognorm
from scipy.optimize import curve_fit
from assemble_pg_network import normalized_length_distribution, process_distribution_string

# Y-values of pixels measured from top of image 
IMG_H = 556;
Obermann_Fig4_Pixel_Data = IMG_H - np.array([443, 318, 257, 204, 170, 163, 128, 135, 124, 160, 137, 161, 158, 157, 161, 179, 202, 218, 217, 227, 271, 243, 264, 303, 315, 287, 308, 357, 358, 365])
Obermann_Unit_Pixel_Data = IMG_H - np.array([415]*len(Obermann_Fig4_Pixel_Data))
Obermann_Offset_Pixels = IMG_H - 490;
Obermann_Cylindrical_Data = (Obermann_Fig4_Pixel_Data - Obermann_Offset_Pixels) / (Obermann_Unit_Pixel_Data - Obermann_Offset_Pixels)
Obermann_DSU_lengths = np.arange(1,len(Obermann_Cylindrical_Data)+1)

Experimental_Average_Chain_Length = 27.8;
Short_Chains_Expectation = sum(Obermann_DSU_lengths*Obermann_Cylindrical_Data*0.01);

fraction_of_total_glycans_2_to_30 = 1.00 - 0.14; # Figure 2, Obermann 1994 -> But it gives the wrong mean length compared to their own measurements?

tx = Obermann_DSU_lengths[1:];
ty = Obermann_Cylindrical_Data[1:] * fraction_of_total_glycans_2_to_30 * 0.01;

def gamma_PDF(x, a_G, loc_G, theta_G):
    return gamma.pdf(x, a_G, loc_G, theta_G)

def FS_WPDF(x, p):
    return (x)*((1-p)**2)*(p**(x-1));

def lognorm_PDF(x, LN1, LN2, LN3):
    return lognorm.pdf(x, LN1, LN2, LN3)

Experimental_Average_Chain_Length = 27.8;
alpha_FS = round(1-(2/(Experimental_Average_Chain_Length + 1)),3);

params_LN, covariance_LN = curve_fit(lognorm_PDF,tx,ty,[0.5,-11,30]);
params_FS, covariance_FS = curve_fit(FS_WPDF,tx,ty,[0.93]);

print(params_FS)
alpha_FS = params_FS[0]
aWFS,bWFS = normalized_length_distribution(process_distribution_string(f"WFS=2=100={alpha_FS}", 999))
aFS,bFS = normalized_length_distribution(process_distribution_string(f"FS=2=100={alpha_FS}", 999))
aLN,bLN = normalized_length_distribution(process_distribution_string(f"LN=2=100={params_LN[0]}={params_LN[1]}={params_LN[2]}", 999))
plt.scatter(tx, ty,label="Experimental Results, Obermann 1994")
plt.plot(aWFS,bWFS,label=r"Flory-Schulz (Weight Fraction), $\alpha=$"+str(alpha_FS))
plt.plot(aFS,bFS,label=r"Flory-Schulz, $\alpha=$"+str(alpha_FS))
plt.plot(aLN,bLN,label=r"Log-Norm")
plt.ylabel("Relative Amount % (Mass Fraction)")
plt.xlabel("Chain Length")
plt.legend()
plt.grid()
plt.show()