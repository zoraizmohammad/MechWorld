from process_elastic_tensor import full_moduli_figure
import os
from utils_helpers import PROJECT_ROOT_DIR

working_directory = os.path.join(PROJECT_ROOT_DIR,"results","flory-schulz-0925")

full_moduli_figure(working_directory,r".*\.elastic_constants")
