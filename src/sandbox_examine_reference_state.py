from utils_helpers import PROJECT_ROOT_DIR
from process_bond_strain import full_bonds_strain_figure
import os.path

prestr_0 = 0.0;
prestr_f = 0.2;

results_dir = os.path.join(PROJECT_ROOT_DIR,"results","093-FS");
filename_0_pattern = r"job12936910\.28.*_prestr"+str(prestr_0).replace(".",r"\.");
filename_f_pattern = r"job12936910\.28.*_prestr"+str(prestr_f).replace(".",r"\.");

full_bonds_strain_figure(results_dir, filename_0_pattern, filename_f_pattern, r"$\mathcal{E} = "+str(prestr_0)+"$", r"$\mathcal{E} = "+str(prestr_f)+"$")