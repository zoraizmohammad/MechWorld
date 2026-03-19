from utils_helpers import find_files, get_confidence_intervals, add_curve_with_ci
import os
import re
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from os import listdir
import matplotlib.pyplot as plt

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
    Vyx  : float = None;
    units : str = "MPa*nm";

    def calculate_orthotropic_moduli(self) -> None:
        # Theory of Plates & Shells, Colorado State University, 2006 -> Reduced Stiffness Matrix
        # Note that C in this struct is the STIFFNESS matrix [Q] in that document's notation 
        self.Gxy = self.C33;
        self.Vxy = self.C12 / self.C22;
        self.Vyx = self.C12 / self.C11;
        denominator = 1 - (self.C12**2)/(self.C11 * self.C22);
        self.Ex = self.C11 * denominator;
        self.Ey = self.C22 * denominator;
    
    def calculate_orthotropic_moduli_compliance(self) -> None:
        M = np.array([[self.C11, self.C12, 0],
                      [self.C12, self.C22, 0],
                      [0,        0,        self.C33]]);
        Minv = np.linalg.inv(M)
        self.Ex = 1 / Minv[0,0];
        self.Ey = 1 / Minv[1,1];
        self.Gxy = 1 / Minv[2,2];
        self.Vxy = -1 * Minv[1,0] * self.Ex;
        self.Vyx = -1 * Minv[1,0] * self.Ey;

    def print_comparison_of_two_moduli_methods(self) -> None:
        self.calculate_orthotropic_moduli();
        print(self.line_data());
        self.calculate_orthotropic_moduli_compliance();
        print(self.line_data());
    
    def expected_stress_ratio_xx_over_yy(self) -> float:
        return (self.C11+self.C12)/(self.C12+self.C22)

    def line_data(self) -> str:
        return f"{self.strain} {self.C11} {self.C22} {self.C33} {self.C12} {self.C13} {self.C23} {self.Ex} {self.Ey} {self.Gxy} {self.Vxy} {self.Vyx} {self.units}\n"

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
        combined_filepath = basepath + ".moduli"

        if not os.path.exists(combined_filepath):
            with open(combined_filepath, "w+") as f:
                f.write("strain C11 C22 C33 C12 C13 C23 Ex Ey Gxy Vxy Vyx units\n");

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
                Vyx = None,
                units = str(line_data[7]).strip(),
            )
            print(struct.line_data())
            struct.calculate_orthotropic_moduli()

            with open(combined_filepath, "a+") as f:
                f.write(struct.line_data());

            #os.remove(filepath);

def import_ElasticTensorStructs_from_file(filepath : str) -> list[ElasticTensorStruct]:
    structs = list()
    with open(filepath,"r") as f:
        lines = f.readlines();
        for i,line in enumerate(lines):
            
            if i == 0: continue;

            line_data = line.split(" ")
            struct = ElasticTensorStruct(
                strain= float(line_data[0]), 
                C11   = float(line_data[1]),
                C22   = float(line_data[2]),
                C33   = float(line_data[3]),
                C12   = float(line_data[4]),
                C13   = float(line_data[5]),
                C23   = float(line_data[6]),
                Ex    = float(line_data[7]),
                Ey    = float(line_data[8]),
                Gxy   = float(line_data[9]),
                Vxy   = float(line_data[10]),
                Vyx   = float(line_data[11]),
                units = str(line_data[12]).strip(),
            )

            assert struct.units == "MPa*nm"

            structs.append(struct);

    return structs

def collect_combined_elastic_dataframe(dirpath : str, regex_pattern : str) -> list[pd.DataFrame]:
    combined_df : pd.DataFrame = "-";
    
    # Returns a list of dataframes, one from each file
    for filename in listdir(dirpath):
        if re.search(regex_pattern, filename):
            #print(f"{filename} is a match")
            filepath = os.path.join(dirpath,filename)
            dataclasses_from_file = import_ElasticTensorStructs_from_file(filepath)
            df = pd.DataFrame([asdict(n) for n in dataclasses_from_file])

            if type(combined_df) == str:
                combined_df = df;
            else:
                combined_df = pd.concat([combined_df,df])
            
    if (type(combined_df) == str):
        raise FileNotFoundError(f"No files were found in: {dirpath} matching regex: {regex_pattern}");

    return combined_df;

## TODO: Check reduced stiffness matrix for unstable modes, look at eigenvalues

## PLOTTING FUNCTIONS -- Ex,Ey,Gxy
def add_moduli_curves(df : pd.DataFrame, color_name : str, labelstr : str):
    # Ex
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'Ex');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle=":", label="Ex : " + labelstr)
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2, 
        label=f'95% Confidence (nSamples={n})'
    )

    # Ey
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'Ey');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="--", label="Ey")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2
    )

    # Gxy
    ci_df = get_confidence_intervals(df, 0.95, 'strain', 'Gxy');
    n = int(len(df)/len(ci_df))
    plt.plot(ci_df.index, ci_df['mean'], color=color_name, linestyle="-", label="Gxy")
    plt.fill_between(
        ci_df.index,
        ci_df['lower'],
        ci_df['upper'],
        color=color_name, 
        alpha=0.2
    )

def finish_moduli_curve():
    plt.legend();
    plt.title("Elastic Moduli vs Strain")
    plt.ylabel("MPa*nm")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid(True);
    plt.show();

def full_moduli_figure(working_dir, regex_pattern, Yao1999 : bool):
    df = collect_combined_elastic_dataframe(working_dir, regex_pattern)
    add_moduli_curves(df, "black", "a = 0.925")
    finish_moduli_curve()

## SIMPLIFIED ESTIMATES OF WHAT THE YAO1999/XU1996 DISPLACEMENT TEST WOULD MEASURE FOR THIS NETWORK
# YAO 1999 uses analysis procedure from XU 1996, which assumes a single isotropic modulus in the network.
# Most likely we will not need 

def add_Yao1999_regions(df):
    plt.fill_between(
        x = [min(df['strain']),max(df['strain'])],
        y1 = [15*12, 15*12],
        y2 = [30*12, 30*12],
        alpha = 0.2,
        color = "orange",
        label = "Ex, Yao1999")
    
    plt.fill_between(
        x = [min(df['strain']),max(df['strain'])],
        y1 = [35*12, 35*12],
        y2 = [60*12, 60*12],
        alpha = 0.2,
        color = "green",
        label = "Ey, Yao1999")

def add_simple_compensation_for_Xu1996_curves(df : pd.DataFrame, color_name : str, labelstr : str):
    # 'Ex'
    # Simplified compensation, actual function would be complex product of slot geometry and Ex Ey Vxy Vyx Gxy
    # this compensation notes that Xu1996 can only measure the magnitude of the stress but cannot know what component it comes from
    # so, it will attribute the all stresses to a single modulus. Assume no shear.
    df["Xu1996_Ex"] = np.sqrt(df['Ex']**2 + df['Vxy']*df['Ey']**2)
    df["Xu1996_Ey"] = np.sqrt(df['Ey']**2 + df['Vyx']*df['Ex']**2)

    add_curve_with_ci(df, 'strain', 'Xu1996_Ex', ":")
    add_curve_with_ci(df, 'strain', 'Xu1996_Ey', "--")

def simple_compensation_for_Xu1996_figure(working_dir, regex_pattern):
    df = collect_combined_elastic_dataframe(working_dir, regex_pattern)
    add_simple_compensation_for_Xu1996_curves(df, "black", "a = 0.925")
    add_Yao1999_regions(df);
    finish_simple_compensation_for_Xu1996_curve();

def finish_simple_compensation_for_Xu1996_curve():
    plt.legend();
    plt.title("Moduli vs Strain, as would be measured by Yao1996/Xu1996")
    plt.ylabel("MPa*nm")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid(True);
    plt.show();

## PLOTTING FUNCTIONS -- Vxy,Vyx

## PLOTTING FUNCTIONS -- Predicted Stress Ratio & Actual Stress Ratio
from process_network_ensembles import add_tension_ratio_curve

def add_expected_tension_ratio(df : pd.DataFrame):
    df["xx_yy_ratio"] = (df["Ex"] + df['Vxy']*df['Ey']) / (df["Ey"] + df['Vyx']*df['Ex']);
    pass

def full_ratios_figure(working_dir, regex_pattern):
    df = collect_combined_elastic_dataframe(working_dir, regex_pattern)
    add_moduli_curves(df, "black", "a = 0.925")
    finish_moduli_curve()