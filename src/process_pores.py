from import_data_from_dumps import import_2D_triclinic_box_bounds_from_dump, import_atoms_from_dump, import_bonds_from_dump, reconstruct_molecule_objects
from assemble_pg_network import shortest_path_is_periodic_x, shortest_path_is_periodic_y
from lammps_PG_objects import Atom, Bond, Angle, GlycanMolecule
from os.path import splitext
import os.path
from simulation_constants_settings import DSU
import numpy as np
import re

import matplotlib.pyplot as plt
from matplotlib.image import imread

def save_monochrome_png_of_network(atoms, bonds, triclinic_bounds, save_to_filepath):
    print(f"Exporting monochrome network image to file: {save_to_filepath}")
    (xlo, xhi, xy, ylo, yhi) = triclinic_bounds;
    
    fig, ax = plt.subplots(frameon=False)

    linewidth = 2;
    
    for b in bonds.values():
            
        a1 = atoms[b.atom_id_1];
        a2 = atoms[b.atom_id_2];

        x1 = a1.x; y1 = a1.y;
        x2 = a2.x; y2 = a2.y;

        #if shortest_path_is_periodic_x(a1, a2, xhi-xlo) or shortest_path_is_periodic_y(a1, a2, yhi-ylo):
        #    continue

        #ax.plot([x1,x2],[y1,y2], color="black", linewidth=linewidth);

        if shortest_path_is_periodic_x(a1, a2, xhi-xlo):
            if x1 > x2:
                x1 = (x1-(xhi-xlo), x1);
                x2 = (x2, x2+(xhi-xlo));
            else:
                x1 = (x1, x1+(xhi-xlo));
                x2 = (x2-(xhi-xlo), x2);
        
        if shortest_path_is_periodic_y(a1, a2, yhi-ylo):
            if y1 > y2:
                y1 = (y1-(yhi-ylo), y1);
                y2 = (y2, y2+(yhi-ylo));
            else:
                y1 = (y1, y1+(yhi-ylo));
                y2 = (y2-(yhi-ylo), y2);

        # Big ol'd bonds
        if (type(x1) == float) & (type(y1) == float):
            ax.plot([x1,x2],[y1,y2], color="black", linewidth=linewidth);
    
        if (type(x1) == tuple) & (type(y1) == float):
            ax.plot([x1[0],x2[0]],[y1,y2], color="black", linewidth=linewidth);
            ax.plot([x1[1],x2[1]],[y1,y2], color="black", linewidth=linewidth);
        
        if (type(x1) == float) & (type(y1) == tuple):
            ax.plot([x1,x2],[y1[0],y2[0]], color="black", linewidth=linewidth);
            ax.plot([x1,x2],[y1[1],y2[1]], color="black", linewidth=linewidth);
    
        if (type(x1) == tuple) & (type(y1) == tuple):
            ax.plot([x1[0],x2[0]],[y1[0],y2[0]], color="black", linewidth=linewidth);
            ax.plot([x1[1],x2[1]],[y1[1],y2[1]], color="black", linewidth=linewidth);
    
    ax.set_xlim(xlo,xhi);
    ax.set_ylim(ylo,yhi);

    DSU_x = (xhi - xlo)/DSU;
    DSU_y = (yhi - ylo)/DSU;

    fig.set_size_inches(DSU_x/10,DSU_y/10)
    fig.set_dpi(10);

    dpi = fig.get_dpi();
    inches_x, inches_y = fig.get_size_inches();
    
    ratio_x = (dpi * inches_x) / DSU_x;
    ratio_y = (dpi * inches_y) / DSU_y;

    output = save_to_filepath;
    fig.savefig(output, bbox_inches='tight', pad_inches=0)
    print(f"Saved image to {output}. Resolution: {ratio_x}, {ratio_y} px / DSU")

    return output

def pizza_boy(filename, disregard_tail_of_fraction = 0.01) -> list[set[tuple[int,int]]]:
    # I'll have a Coke
    image_data = imread(filename);
    boolean_image_data = bool_me(image_data);
    gossamer, unclaimed = establish_gossamer_and_unclaimed_sets(boolean_image_data)
    print(len(gossamer), len(unclaimed))

    # I'll have a Pepsi now
    pores : list[set[tuple[int,int]]] = list();

    # You are afraid
    cutoff = len(unclaimed) * max(disregard_tail_of_fraction, 0)
    while len(unclaimed) > cutoff:
       whatever_pixel_idc = next(iter(unclaimed))
       newest_freshness_pore = set();
       flood_fill_PBC_less_recursion(newest_freshness_pore, whatever_pixel_idc, boolean_image_data);
       pores.append(newest_freshness_pore)
       [unclaimed.remove(bro) for bro in newest_freshness_pore]
       print(f"Found Pore with Area: {len(newest_freshness_pore)}. Remaining unclaimed pixels: {len(unclaimed)}")

    # That you're a Pizza Boy
    return pores

def bool_me(img_data : np.typing.NDArray):
    nx, ny, nz = np.shape(img_data);

    not_pore_img_data = np.array((nx,ny),dtype=bool);
    completely_white_img = ((img_data[:,:,1] == 1) & (img_data[:,:,2] == 1) & (img_data[:,:,3] == 1));
    completely_opaque_img = (img_data[:,:,3] == 1);
    not_pore_img_data = ~(completely_white_img) | ~(completely_opaque_img);

    return not_pore_img_data;

def establish_gossamer_and_unclaimed_sets(boolean_image_data : np.typing.NDArray):
    gossamer_pixels = set();
    unclaimed_pixels = set();

    print(np.shape(boolean_image_data))

    nx, ny = np.shape(boolean_image_data);

    # https://numpy.org/doc/stable/reference/arrays.nditer.html
    it = np.nditer(boolean_image_data, flags=['multi_index'])
    for x in it:
        if x:
            gossamer_pixels.add(it.multi_index);
        else:
            unclaimed_pixels.add(it.multi_index);
    
    return gossamer_pixels, unclaimed_pixels;       

def get_apx(px, nx, ny) -> tuple[int,int]:
    if px[1] == ny-1:
        return (px[0], 0)
    else:
        return (px[0], px[1]+1)
    
def get_bpx(px, nx, ny) -> tuple[int,int]:
    if px[1] == 0:
        return (px[0], ny-1)
    else:
        return (px[0], px[1]-1)
    
def get_rpx(px, nx, ny) -> tuple[int,int]:
    if px[0] == nx-1:
        return (0, px[1])
    else:
        return (px[0]+1, px[1])
    
def get_lpx(px, nx, ny) -> tuple[int,int]:
    if px[0] == 0:
        return (nx-1, px[1])
    else:
        return (px[0]-1, px[1])

# Same idea as https://en.wikipedia.org/wiki/Flood_fill#Span_filling
def flood_fill_PBC_less_recursion(pixels_in_pore : set[tuple[int,int]], r0 : tuple[int,int], boolean_image_data : np.typing.NDArray) -> set[tuple[int,int]]:
    upward_seeds = set();
    downward_seeds = set();
    nx, ny = np.shape(boolean_image_data);
    
    pixels_in_pore.add(r0);
    upward_seeds.add(get_apx(r0, nx, ny));
    downward_seeds.add(get_bpx(r0, nx, ny));

    # Span right
    rpx = get_rpx(r0, nx, ny);
    while (not boolean_image_data[rpx]):
        pixels_in_pore.add(rpx);
        upward_seeds.add(get_apx(rpx, nx, ny));
        downward_seeds.add(get_bpx(rpx, nx, ny));
        rpx = get_rpx(rpx, nx, ny);
    
    # Span left
    lpx = get_lpx(r0, nx, ny);
    while (not boolean_image_data[lpx]):
        pixels_in_pore.add(lpx);
        upward_seeds.add(get_apx(lpx, nx, ny));
        downward_seeds.add(get_bpx(lpx, nx, ny));
        lpx = get_lpx(lpx, nx, ny);
    
    # Seeds
    for px in upward_seeds.union(downward_seeds):
        if (px not in pixels_in_pore) and (not boolean_image_data[px]):
            flood_fill_PBC_less_recursion(pixels_in_pore, px, boolean_image_data);      

def disregard_pores_based_on_pixel_area_criteria(pores : list[set[tuple[int,int]]], Amin = None, Amax = None) -> list[set[tuple[int,int]]]:
    filtered_pores = list();
    for p in pores:
        if ((Amin == None) or (len(p) >= Amin)) and ((Amax == None) or (len(p) <= Amax)):
            filtered_pores.append(p);
            continue;
    print(f"Filtered pores based on size criteria: {len(pores)} unfiltered => {len(filtered_pores)} filtered")
    return filtered_pores;

def calculate_array_of_areas(list_pxs_in_pore : list[set[tuple[int,int]]], scale_px_to_DSU : float):
    areas = np.zeros(len(list_pxs_in_pore));
    for i,pxs_in_pore in enumerate(list_pxs_in_pore):
        areas[i] = len(pxs_in_pore) / (scale_px_to_DSU)**2;
    return areas

def calculate_center_of_pore(pxs_in_pore : set[tuple[int,int]], triclinic_bounds : tuple[float,float,float,float,float]):
    pass

# Pore Sets Save/Load
def save_comprehensive_pores_data(list_pores : list[set[tuple[int,int]]], save_to_filepath : str):
    with open(save_to_filepath, "w") as f:
        for pore in list_pores:
            for px in pore:
                f.write(f"({px[0]},{px[1]}) ")
            f.write("\n")

def load_comprehensive_pores_data(load_from_filepath : str):
    pores : list[set[tuple[int,int]]] = list();
    with open(load_from_filepath, "r") as f:
        for line in f.readlines():
            pores.append(set());
            list_of_px_tuple_str = line.split(" ")
            for px_tuple_str in list_of_px_tuple_str:
                #print(px_tuple_str)
                match = re.match(r"\((-?\d+),(-?\d+)\)", px_tuple_str)

                if match != None:
                    pores[-1].add((int(match.group(1)),int(match.group(2))));
    
    print(f"Loaded {len(pores)} pores from file {load_from_filepath}")

    return pores

# Pore Areas Save/Load - much faster
def save_pores_areas(pore_areas : list[float], save_to_filepath : str):
    with open(save_to_filepath, "w") as f:
        for a in pore_areas:
            f.write(f"{str(a)}\n")

def load_pores_areas(load_from_filepath : str):
    pores : list[float] = list();
    with open(load_from_filepath, "r") as f:
        for line in f.readlines():
            pores.append(float(line.strip()))
    print(f"Loaded {len(pores)} areas from file {load_from_filepath}")
    return np.array(pores)

def calculate_pixel_scale(filename, triclinic_bounds):
    img_data = imread(filename);

    xDSU = triclinic_bounds[1] - triclinic_bounds[0];
    xPX, _, _ = np.shape(img_data);

    return (xPX / xDSU);

#### Produce a figure comparing the initial state and final state of orientation, like Xaoxuan Figure 4B-D
def get_pore_area_array(filepath : str, use_cached_results : bool, min_area_sqDSU : float) -> np.ndarray:
    
    # do some light sanitization of the filepath, remove potential extensions
    if str(filepath).endswith(".atoms") or str(filepath).endswith(".bonds") or str(filepath).endswith(".pores"):
        filepath = os.path.splitext(filepath)[0];
    
    # These are the corresponding files for this network
    atoms_filepath = filepath + ".atoms"
    bonds_filepath = filepath + ".bonds"
    image_filepath = filepath + ".png"
    pores_filepath = filepath + ".pores"
    areas_filepath = filepath + ".pareas"

    # Import atoms and bonds from dumps
    triclinic_bounds = import_2D_triclinic_box_bounds_from_dump(atoms_filepath);
    atoms = import_atoms_from_dump(atoms_filepath, triclinic_bounds);
    bonds = import_bonds_from_dump(bonds_filepath);
    molecules = reconstruct_molecule_objects(atoms, bonds);

    for m in molecules.values():
        m.delete_if_free(atoms, bonds, None)

    # If needed, create a black and white image for the flood fill algorithm
    if os.path.exists(image_filepath) and use_cached_results:
        pass
    else:
        save_monochrome_png_of_network(atoms, bonds, triclinic_bounds, image_filepath);
    
    scale_px_to_DSU = calculate_pixel_scale(image_filepath, triclinic_bounds);

    # Either load pores from file, or run flood fill to create said file
    if os.path.exists(areas_filepath) and (use_cached_results):
        pore_areas = load_pores_areas(areas_filepath);
    else:
        if os.path.exists(pores_filepath) and (use_cached_results):
            pixels_sorted_by_pore = load_comprehensive_pores_data(pores_filepath);
        else:
            pixels_sorted_by_pore = pizza_boy(image_filepath, 0.01) # The last 1% of pixels usually has areas of 1-10 px2, which would be filtered out anyway
            pixels_sorted_by_pore = disregard_pores_based_on_pixel_area_criteria(pixels_sorted_by_pore, min_area_sqDSU*(scale_px_to_DSU)*(scale_px_to_DSU), None);
            save_comprehensive_pores_data(pixels_sorted_by_pore, pores_filepath);
        
        pore_areas : np.ndarray = calculate_array_of_areas(pixels_sorted_by_pore, scale_px_to_DSU);
        save_pores_areas(pore_areas, areas_filepath);

    return pore_areas;

def collect_combined_pore_area_array(dirpath : str, regex_pattern : str, use_cached_results, min_area_sqDSU) -> np.ndarray:
    # Returns a list of dataframes, one from each file
    combined_areas = 0;
    matches_counter = 0;

    for filename in os.listdir(dirpath):
        if re.search(regex_pattern, filename):
            filepath = os.path.join(dirpath, filename)
            new_areas = get_pore_area_array(filepath, use_cached_results, min_area_sqDSU)

            if type(combined_areas) == int:
                combined_areas = new_areas;
            else:
                combined_areas = np.append(combined_areas, new_areas)

            matches_counter += 1;

    if matches_counter == 0:
        raise FileNotFoundError()

    return combined_areas

def full_pore_sizes_file_figure(curves_info : tuple[str, str, str, str], use_cached_results = True, min_area_sqDSU : float = 1, ax : plt.Axes = None):

    if not ax:
        ax = plt.subplot();
    
    max_area = 0;
    n_bins = 100;

    for curve_info in curves_info:
        (curve_dir, curve_filename, curve_label, curve_color) = curve_info;

        filepath = os.path.join(curve_dir,curve_filename)
        pore_areas : np.ndarray = get_pore_area_array(filepath, use_cached_results, min_area_sqDSU);

        max_area = max(max_area, max(pore_areas))

        # Add histogram for this data
        ax.hist(pore_areas, bins = n_bins, alpha=0.3, density=True, log=True, color=curve_color, label=curve_label);

    ax.legend()
    ax.set_title("Pore Area Distributions")
    ax.set_ylabel("Fraction of Pores")
    ax.set_xlabel("Area ${L_{DSU}}^2$")
    ax.set_xlim(0,max_area);
    plt.show()

def full_pore_sizes_regex_figure(curves_info : tuple[str, str, str, str], use_cached_results = True, min_area_sqDSU : float = 1, ax : plt.Axes = None):

    axes_not_provided : bool = (ax == None);

    if axes_not_provided:
        ax = plt.subplot();
    
    max_area = 0;
    n_bins = 100;

    for curve_info in curves_info:
        (curve_dir, curve_regex, curve_label, curve_color) = curve_info;

        combined_pore_areas : np.ndarray = collect_combined_pore_area_array(curve_dir, curve_regex, use_cached_results, min_area_sqDSU);

        max_area = max(max_area, max(combined_pore_areas))

        # Add histogram for this data
        ax.hist(combined_pore_areas, bins = n_bins, alpha=0.3, density=False, log=True, color=curve_color, label=curve_label);

    ax.legend()
    ax.set_title("Pore Area Distributions")
    ax.set_ylabel("Fraction of Pores")
    ax.set_xlabel("Area ${L_{DSU}}^2$")
    ax.set_xlim(0,max_area);

    if axes_not_provided:
        plt.show()