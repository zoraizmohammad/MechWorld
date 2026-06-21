from process_orientation import full_oriented_stress_figure
from utils_helpers import PROJECT_ROOT_DIR
import os

working_dir = os.path.join(PROJECT_ROOT_DIR,"results","093-FS")
regex = r"job12939337.*prestr0\.3\.atoms"

full_oriented_stress_figure(working_dir, regex)

# todo:
# Add axis labels 
# Add titles
# Fix/ignore orientation of periodic glycan strands