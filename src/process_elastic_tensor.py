from utils_helpers import find_files
import os
import re
from dataclasses import dataclass

@dataclass
class ElasticTensorStruct:
    strain : float;
    C11 : float;
    C22 : float;
    C33 : float;
    C12 : float;
    C13 : float;
    C23 : float;
    Ex   : float = None;
    Ey   : float = None;
    Gxy  : float = None;
    Vxy  : float = None;
    units : str = "MPa";

    def calculate_orthotropic_moduli(self) -> None:
        # Theory of Plates & Shells, Colorado State University, 2006 -> Reduced Stiffness Matrix
        # Note that C in this struct is the STIFFNESS matrix [Q] in that document's notation 
        self.Gxy = 1/2 * self.C33;
        self.Vxy = self.C12 / self.C22;
        denominator = 1 - (self.C12**2)/(self.C11 * self.C22);
        self.Ex = self.C11 * denominator;
        self.Ey = self.C22 * denominator;

    def line_data(self) -> str:
        return f"{self.strain} {self.C11} {self.C22} {self.C33} {self.C12} {self.C13} {self.C23} {self.Ex} {self.Ey} {self.Gxy} {self.Vxy} {self.units}\n"
        

def combine_elastic_constant_files_into_one_file_per_network(working_dir : str):
    set_of_unique_basepaths = set();
    regex_individual_constants = r".+_prestr\d\.\d+\.elastic_constants";
    regex_capture_basepaths = r"(.+)_prestr\d\.\d+\.elastic_constants";

    filepaths_to_individual_lines : set[str] = find_files(working_dir, regex_individual_constants);

    #print(filepaths_to_individual_lines);

    for filepath in filepaths_to_individual_lines:
        match = re.match(regex_capture_basepaths, filepath);
        if match:
            basepath = match.group(1);
            set_of_unique_basepaths.add(basepath);

    #print(set_of_unique_basepaths);

    for basepath in set_of_unique_basepaths:
        combined_filepath = basepath + ".elastic_constants"

        if not os.path.exists(combined_filepath):
            with open(combined_filepath, "w+") as f:
                f.write("strain C11 C22 C33 C12 C13 C23 Ex Ey Gxy Vxy units\n");

        for filepath in sorted(list(filepaths_to_individual_lines)):
            if not filepath.startswith(basepath):
                continue;
            
            line : str = "";
            with open(filepath, "r") as f:
                line = f.readline();
            
            line_data = line.split(" ")
            struct = ElasticTensorStruct(
                strain= float(line_data[0]), 
                C11   = float(line_data[1]),
                C22   = float(line_data[2]),
                C33   = float(line_data[3]),
                C12   = float(line_data[4]),
                C13   = float(line_data[5]),
                C23   = float(line_data[6]),
                Ex = None,
                Ey = None,
                Gxy = None,
                Vxy = None,
                units = str(line_data[7]).strip(),
            )
            print(struct.line_data())
            struct.calculate_orthotropic_moduli()

            with open(combined_filepath, "a+") as f:
                f.write(struct.line_data());

            #os.remove(filepath);

def import_data_from_elastic_constant_file(filepath : str):
    pass