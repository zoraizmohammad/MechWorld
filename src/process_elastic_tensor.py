from utils_helpers import find_files, get_confidence_intervals, add_curve_with_ci, get_initial_density_from_filename, get_crosslinkage_from_filename, apply_band_filters_to_df
from simulation_constants_settings import DSU
import os
import re
import tempfile
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
    tension_ratio_xx_over_yy : float = None;
    positive_definite : bool = None;

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
    
    def calculate_tension_ratio_xx_over_yy(self) -> float:
        self.tension_ratio_xx_over_yy = (self.C11+self.C12)/(self.C12+self.C22)

    def line_data(self) -> str:
        return f"{self.strain} {self.C11} {self.C22} {self.C33} {self.C12} {self.C13} {self.C23} {self.Ex} {self.Ey} {self.Gxy} {self.Vxy} {self.Vyx} {self.units}\n"

    def get_stiffness_tensor(self) -> np.ndarray:
        return np.array([[self.C11, self.C12, self.C13],
                         [self.C12, self.C22, self.C23],
                         [self.C13, self.C23, self.C33]])

    def calculate_positive_definite(self):
        eigenvalues = np.linalg.eigvalsh(self.get_stiffness_tensor())
        self.positive_definite = np.all(eigenvalues > 0) # note to self that .all() exists

def _read_individual_elastic_constant(filepath : str) -> ElasticTensorStruct:
    with open(filepath, "r", encoding="utf-8") as source:
        line_data = source.readline().split()
    if len(line_data) != 8:
        raise ValueError(
            f"Expected 8 fields in elastic-constant record {filepath}; "
            f"received {len(line_data)}"
        )

    struct = ElasticTensorStruct(
        strain=float(line_data[0]),
        C11=float(line_data[1]),
        C22=float(line_data[2]),
        C33=float(line_data[3]),
        C12=float(line_data[4]),
        C13=float(line_data[5]),
        C23=float(line_data[6]),
        units=line_data[7],
    )
    struct.calculate_orthotropic_moduli()
    return struct


def combine_elastic_constant_files_into_one_file_per_network(
        working_dir : str) -> list[str]:
    """Create deterministic per-network summaries without mutating raw records."""
    individual_pattern = re.compile(
        r"^(?P<base>.+)_prestr[+-]?(?:\d+(?:\.\d*)?|\.\d+)\.elastic_constants$"
    )
    grouped_filepaths : dict[str, list[str]] = {}
    for filename in sorted(listdir(working_dir)):
        match = individual_pattern.fullmatch(filename)
        if not match:
            continue
        filepath = os.path.join(working_dir, filename)
        if os.path.isfile(filepath):
            grouped_filepaths.setdefault(match.group("base"), []).append(filepath)

    combined_paths = []
    header = "strain C11 C22 C33 C12 C13 C23 Ex Ey Gxy Vxy Vyx units\n"
    for basename in sorted(grouped_filepaths):
        structs = [
            _read_individual_elastic_constant(filepath)
            for filepath in grouped_filepaths[basename]
        ]
        structs.sort(key=lambda item: item.strain)

        strains = np.asarray([item.strain for item in structs], dtype=float)
        if not np.all(np.isfinite(strains)):
            raise ValueError(f"Network {basename} contains non-finite strain")
        if len(np.unique(strains)) != len(strains):
            raise ValueError(f"Network {basename} contains duplicate strain records")
        units = {item.units for item in structs}
        if len(units) != 1:
            raise ValueError(f"Network {basename} mixes elastic units: {sorted(units)}")

        combined_filepath = os.path.join(working_dir, basename + ".moduli")
        # Write a complete replacement and atomically install it. This makes a
        # repeated invocation byte-identical while retaining every raw input.
        with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                prefix=basename + ".moduli.",
                suffix=".tmp",
                dir=working_dir,
                delete=False) as temporary:
            temporary.write(header)
            for struct in structs:
                temporary.write(struct.line_data())
            temporary_path = temporary.name
        try:
            os.replace(temporary_path, combined_filepath)
        except BaseException:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise
        combined_paths.append(combined_filepath)

    return combined_paths

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

            struct.calculate_tension_ratio_xx_over_yy()
            struct.calculate_positive_definite()

            structs.append(struct);

    return structs

def collect_combined_elastic_dataframe(dirpath : str, regex_pattern : str) -> pd.DataFrame:
    combined_df : pd.DataFrame = "-";
    files_found_cnt = 0;
    
    for filename in sorted(listdir(dirpath)):
        if re.search(regex_pattern, filename):
            #print(f"{filename} is a match")
            filepath = os.path.join(dirpath,filename)
            dataclasses_from_file = import_ElasticTensorStructs_from_file(filepath)
            df = pd.DataFrame([asdict(n) for n in dataclasses_from_file])
            df['rho_0'] = [get_initial_density_from_filename(filename)] * len(df);
            df['rho_f'] = df["rho_0"] / (1+df["strain"])**2;
            df['ratio'] = df["tension_ratio_xx_over_yy"];
            df['network_id'] = [os.path.splitext(filename)[0]] * len(df);

            linkage = get_crosslinkage_from_filename(filename);
            if linkage: df['linkage'] = [linkage] * len(df);

            if type(combined_df) == str:
                combined_df = df;
            else:
                combined_df = pd.concat([combined_df,df]);
    
            files_found_cnt += 1;
            
    if (type(combined_df) == str):
        raise FileNotFoundError(f"No files were found in: {dirpath} matching regex: {regex_pattern}");

    return combined_df, files_found_cnt;


def _strict_monotonic_group(
        frame : pd.DataFrame,
        x_column : str,
        context : str) -> pd.DataFrame:
    if len(frame) < 2:
        raise ValueError(f"{context} needs at least two interpolation states")
    x = frame[x_column].to_numpy(dtype=float)
    if not np.all(np.isfinite(x)):
        raise ValueError(f"{context} contains a non-finite interpolation axis")
    differences = np.diff(x)
    if np.any(differences == 0):
        raise ValueError(f"{context} contains duplicate {x_column} values")
    if np.all(differences > 0):
        return frame.copy().reset_index(drop=True)
    if np.all(differences < 0):
        return frame.iloc[::-1].copy().reset_index(drop=True)
    raise ValueError(f"{context} {x_column} must be strictly monotonic")


def interpolate_grouped_values_at(
        frame : pd.DataFrame,
        target_x : float,
        value_columns : list[str],
        group_column : str = "network_id",
        x_column : str = "strain") -> pd.DataFrame:
    """Interpolate once per independent network, rejecting ambiguous axes."""
    required = [group_column, x_column, *value_columns]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"Grouped interpolation is missing columns: {missing}")
    if not np.isfinite(target_x):
        raise ValueError("Interpolation target must be finite")

    rows = []
    for group_id, group in frame.groupby(group_column, sort=True):
        group = _strict_monotonic_group(
            group, x_column, f"network {group_id!r}"
        )
        axis = group[x_column].to_numpy(dtype=float)
        if target_x < axis[0] or target_x > axis[-1]:
            raise ValueError(
                f"network {group_id!r} target {target_x} is outside "
                f"the {x_column} range [{axis[0]}, {axis[-1]}]"
            )

        row = {group_column: group_id, x_column: target_x}
        for column in value_columns:
            values = group[column].to_numpy(dtype=float)
            if not np.all(np.isfinite(values)):
                raise ValueError(f"network {group_id!r} has non-finite {column}")
            row[column] = float(np.interp(target_x, axis, values))
        rows.append(row)
    return pd.DataFrame(rows, columns=required)

## TODO: Check reduced stiffness matrix for unstable modes, look at eigenvalues

## PLOTTING FUNCTIONS -- Ex,Ey,Gxy
def full_moduli_figure(curves_information : list[tuple[str, str, str, str]], thickness_nm = None):

    for i,curve_tuple in enumerate(curves_information):
        working_dir, regex_pattern, color_name, extra_label_info, curve_filters = curve_tuple;
        df, file_cnt = collect_combined_elastic_dataframe(working_dir, regex_pattern)
        print(f"Curve #{i}: collected {file_cnt} output files from regex pattern")

        df = apply_band_filters_to_df(df, curve_filters);

        # convert to MPa if thickness is specified
        if thickness_nm:
            df['Ex'] = df["Ex"]/thickness_nm;
            df['Ey'] = df["Ey"]/thickness_nm;
            df['Gxy'] = df["Gxy"]/thickness_nm;

        add_curve_with_ci(df, 'strain', 'Ex', curve_color=color_name, curve_linestyle="-", curve_label_override="$E_{xx}$"+extra_label_info)
        add_curve_with_ci(df, 'strain', 'Ey', curve_color=color_name, curve_linestyle="--", curve_label_override="$E_{yy}$")
        add_curve_with_ci(df, 'strain', 'Gxy', curve_color=color_name, curve_linestyle=":", curve_label_override="$G_{xy}$")

    plt.legend();

    title_str = "Extensional and Shear Moduli"

    if thickness_nm:
        title_str += "; $t = "+str(thickness_nm)+"nm$"

    plt.title(title_str);

    if thickness_nm:
        plt.ylabel("MPa")
    else:
        plt.ylabel("MPa*nm")

    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid(True);
    plt.show();

## PLOTTING FUNCTIONS -- Vxy,Vyx
def full_poisson_ratios_figure(curves_information : list[tuple[str, str, str, str]]):

    for i,curve_tuple in enumerate(curves_information):
        working_dir, regex_pattern, color_name, extra_label_info, curve_filters = curve_tuple;
        df, file_cnt = collect_combined_elastic_dataframe(working_dir, regex_pattern)
        print(f"Curve #{i}: collected {file_cnt} output files from regex pattern")

        df = apply_band_filters_to_df(df, curve_filters);

        add_curve_with_ci(df, 'strain', 'Vxy',"--", curve_label_override="$V_{xy}$"+extra_label_info,curve_color=color_name)
        add_curve_with_ci(df, 'strain', 'Vyx',":", curve_label_override="$V_{yx}$",curve_color=color_name)
    
    plt.legend()
    plt.title("Poisson Ratios")
    plt.ylabel("Poisson Ratio [a.u.]")
    plt.xlabel(r"$\mathcal{E}$, Strain [a.u.]")
    plt.grid()
    plt.show()

## PLOTTING FUNCTIONS -- Subplots Galore
def full_subplots_figure(curves_information : list[tuple[str, str, str, str, float]], thickness_nm=6.0):

    fig, axes = plt.subplots(2,3, sharey="row", sharex="row", tight_layout=True)

    axes[0,0].set_title(r"$E_{xx}$")
    axes[0,1].set_title(r"$E_{yy}$")
    axes[0,2].set_title(r"$G_{xy}$")
    axes[1,0].set_title(r"$V_{xy}$")
    axes[1,1].set_title(r"$V_{yx}$")
    axes[1,2].set_title(r"$\sigma_{xx} / \sigma_{yy}$")

    for i,curve_tuple in enumerate(curves_information):
        working_dir, regex_pattern, color_name, extra_label_info, curve_filters, print_this_strain = curve_tuple;
        df, file_cnt = collect_combined_elastic_dataframe(working_dir, regex_pattern)
        print(f"Curve #{i}: collected {file_cnt} output files from regex pattern")

        df = apply_band_filters_to_df(df, curve_filters);

        # convert to MPa if thickness is specified
        if thickness_nm:
            df['Ex'] = df["Ex"]/thickness_nm;
            df['Ey'] = df["Ey"]/thickness_nm;
            df['Gxy'] = df["Gxy"]/thickness_nm;

        add_curve_with_ci(df, 'strain', 'Ex',"-", curve_label_override=extra_label_info,curve_color=color_name
            , ax=axes[0,0])
        add_curve_with_ci(df, 'strain', 'Ey',"-", curve_label_override=extra_label_info,curve_color=color_name
            , ax=axes[0,1])
        add_curve_with_ci(df, 'strain', 'Gxy',"-", curve_label_override=extra_label_info,curve_color=color_name
            , ax=axes[0,2])
        add_curve_with_ci(df, 'strain', 'Vxy',"-", curve_label_override=extra_label_info,
            curve_color=color_name, ax=axes[1,0])
        add_curve_with_ci(df, 'strain', 'Vyx',"-", curve_label_override=extra_label_info,curve_color=color_name
            , ax=axes[1,1])
        add_curve_with_ci(df, 'strain', 'ratio',"-", curve_label_override=extra_label_info,curve_color=color_name
            , ax=axes[1,2])
        
        interpolated = interpolate_grouped_values_at(
            df,
            target_x=print_this_strain,
            value_columns=["Ex", "Ey", "Gxy", "Vxy", "Vyx"],
        )
        for column in ("Ex", "Ey", "Gxy", "Vxy", "Vyx"):
            print(
                rf"{column},  $\epsilon_0$ {print_this_strain}",
                interpolated[column].mean(),
            )
    
    axes[0,0].legend()

    for ax in axes.flat:
        ax.grid(True)
        ax.set_xlabel(r"$\mathcal{E}$")

    for ax in axes[1,:]:
        ax.set_ylim(0,None)

    if thickness_nm:
        axes[0,0].set_ylabel(r"$MPa$")
    else:
        axes[0,0].set_ylabel(r"$MPa*nm$")

    axes[1,0].set_ylabel(r"$a.u.$")

    plt.show()

def full_positive_definite_figure(curves_information : list[tuple[str, str, str, str]], ax : plt.Axes = None):
    if ax == None:
        ax = plt.subplot()

    for i, curve_tuple in enumerate(curves_information):
        working_dir, regex_pattern, color_name, extra_label_info, curve_filters = curve_tuple;
        df, file_cnt = collect_combined_elastic_dataframe(working_dir, regex_pattern)
        print(f"Curve #{i}: collected {file_cnt} output files from regex pattern")

        df = apply_band_filters_to_df(df, curve_filters);

        add_curve_with_ci(df, 'strain', 'positive_definite',"-", 
            curve_label_override=extra_label_info,
            curve_color=color_name,
            ax=ax)
    
    ax.set_ylabel("Is stiffness positive definite?")
    ax.set_xlabel(r"$\mathcal{E}$")
    ax.set_ylim([-0.1,1.1])
    plt.show()
