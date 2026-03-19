from process_elastic_tensor import full_moduli_figure, simple_compensation_for_Xu1996_figure
import os
from utils_helpers import PROJECT_ROOT_DIR

working_directory = os.path.join(PROJECT_ROOT_DIR,"results","FS-0925")

full_moduli_figure(working_directory,r".*\.moduli", True)

#simple_compensation_for_Xu1996_figure(working_directory,r".*\.moduli")
