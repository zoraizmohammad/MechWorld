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

def save_png_of_network(atoms, bonds, triclinic_bounds, save_to_filepath, overwrite = True):
    print(f"Exporting monochrome network image to file: {save_to_filepath}")
    (xlo, xhi, xy, ylo, yhi) = triclinic_bounds;
    
    fig, ax = plt.subplots(frameon=False)
    
    for b in bonds.values():
            
        a1 = atoms[b.atom_id_1];
        a2 = atoms[b.atom_id_2];

        if shortest_path_is_periodic_x(a1, a2, xhi-xlo) or shortest_path_is_periodic_y(a1, a2, yhi-ylo):
            continue;

        # Big ol'd bonds
        ax.plot([a1.x,a2.x],[a1.y,a2.y], color="black");
    
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

def disregard_pores_based_on_area_criteria(pores : list[set[tuple[int,int]]], Amin = None, Amax = None) -> list[set[tuple[int,int]]]:
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

def save_pores_data(list_pores : list[set[tuple[int,int]]], save_to_filepath : str):
    with open(save_to_filepath, "w") as f:
        for pore in list_pores:
            for px in pore:
                f.write(f"({px[0]},{px[1]}) ")
            f.write("\n")

def load_pores_data(save_to_filepath : str):
    pores : list[set[tuple[int,int]]] = list();
    with open(save_to_filepath, "r") as f:
        line = f.readline()
        pores.append(set());
        list_of_px_tuple_str = line.split(" ")
        for px_tuple_str in list_of_px_tuple_str:
            print(px_tuple_str)
            match = re.match(r"\((-?\d+),(-?\d+)\)", px_tuple_str)

            if match != None:
                pores[-1].add((int(match.group(1)),int(match.group(2))));

    return pores

def calculate_pixel_scale(filename, triclinic_bounds):
    img_data = imread(filename);

    xDSU = triclinic_bounds[1] - triclinic_bounds[0];
    xPX, _, _ = np.shape(img_data);

    return (xPX / xDSU);

#### Produce a figure comparing the initial state and final state of orientation, like Xaoxuan Figure 4B-D
def full_pore_size_distribution_figure(working_directory, base_filename_no_extensions, use_cached_results = True):
    # skeleton of figure

    base_filepath = os.path.join(working_directory,base_filename_no_extensions)
    
    # relaxed data
    atoms_filepath = base_filepath + ".relaxed.atoms"
    bonds_filepath = base_filepath + ".relaxed.bonds"
    png_filepath  = base_filepath + ".relaxed.png"
    pores_filepath = base_filepath + ".relaxed.pores"

    triclinic_bounds = import_2D_triclinic_box_bounds_from_dump(atoms_filepath);
    atoms = import_atoms_from_dump(atoms_filepath, triclinic_bounds);
    bonds = import_bonds_from_dump(bonds_filepath);
    
    if os.path.exists(png_filepath) and use_cached_results:
        pass
    else:
        save_png_of_network(atoms, bonds, triclinic_bounds, png_filepath, True);
    
    pixels_sorted_by_pore_0 = pizza_boy(png_filepath, 0.1);
    #save_pores_data(pixels_sorted_by_pore_0, pores_filepath)
    #pores2 = load_pores_data(pores_filepath)
    #assert pixels_sorted_by_pore_0 == pores2
    scale_0 = calculate_pixel_scale(png_filepath, triclinic_bounds);
    areas_0 = calculate_array_of_areas(pixels_sorted_by_pore_0, scale_0);

    # final data
    atoms_filepath = base_filepath + ".final.atoms"
    bonds_filepath = base_filepath + ".final.bonds"
    png_filepath  = base_filepath + ".final.png"

    triclinic_bounds = import_2D_triclinic_box_bounds_from_dump(atoms_filepath);
    atoms = import_atoms_from_dump(atoms_filepath, triclinic_bounds);
    bonds = import_bonds_from_dump(bonds_filepath);
    
    if os.path.exists(png_filepath) and use_cached_results:
        pass
    else:
        save_png_of_network(atoms, bonds, triclinic_bounds, png_filepath, True);
    
    pixels_sorted_by_pore_f = pizza_boy(png_filepath, 0.1);
    scale_f = calculate_pixel_scale(png_filepath, triclinic_bounds);
    areas_f = calculate_array_of_areas(pixels_sorted_by_pore_f, scale_f);

    #### Plots
    # add labels and titles
    fig, ax = plt.subplots(1,2);
    
    # Top-Left Plot: Relaxed Length vs Glycan Orientation
    ax[0].hist(areas_0, bins = 500);
    ax[0].set_title("Initial Distribution of Pore Areas")
    ax[0].set_ylabel("Number of Pores")
    ax[0].set_xlabel("Area [DSU^2]")

    ax[1].hist(areas_f, bins = 500);
    ax[1].set_title("Final Distribution of Pore Areas")
    ax[1].set_ylabel("Number of Pores")
    ax[1].set_xlabel("Area [DSU^2]")

    plt.show()