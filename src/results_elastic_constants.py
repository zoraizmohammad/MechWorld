from process_elastic_tensor import full_moduli_figure, full_poisson_ratios_figure
import os
from utils_helpers import PROJECT_ROOT_DIR

working_directory = os.path.join(PROJECT_ROOT_DIR,"results","wpdf-FS-0925")

full_moduli_figure(working_directory,r".*\.moduli")
full_poisson_ratios_figure(working_directory,r".*\.moduli")

#simple_compensation_for_Xu1996_figure(working_directory,r".*\.moduli")
