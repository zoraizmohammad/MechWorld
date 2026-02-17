from import_data_from_dumps import import_2D_triclinic_box_bounds_from_dump, import_atoms_from_dump, import_bonds_from_dump, reconstruct_molecule_objects
from assemble_pg_network import shortest_path_is_periodic_x, shortest_path_is_periodic_y
from lammps_PG_objects import Atom, Bond, Angle, GlycanMolecule
from os.path import splitext
import os.path
from simulation_constants_settings import DSU
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.image import imread

def save_png_of_network(filepath):
    print(f"Exporting monochrome network image to file: {filepath}")
    
    triclinic_bounds = import_2D_triclinic_box_bounds_from_dump(filepath);
    atoms = import_atoms_from_dump(splitext(filepath)[0]+".atoms", triclinic_bounds);
    bonds = import_bonds_from_dump(splitext(filepath)[0]+".bonds");
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

    output = os.path.join(os.path.curdir,"test.png");
    fig.savefig(output, bbox_inches='tight', pad_inches=0)
    print(f"Saved image to {output}. Resolution: {ratio_x}, {ratio_y} px / DSU")

    return output

def pizza_boy(filename) -> list[set[tuple[int,int]]]:
    # I'll have a Coke
    image_data = imread(filename);
    boolean_image_data = bool_me(image_data);
    gossamer, unclaimed = establish_gossamer_and_unclaimed_sets(boolean_image_data)
    print(len(gossamer), len(unclaimed))

    # I'll have a Pepsi now
    pores : list[set[tuple[int,int]]] = list();

    # You are afraid
    while len(unclaimed) > 0:
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

def calculate_center_of_pore(pxs_in_pore : set[tuple[int,int]], triclinic_bounds : tuple[float,float,float,float,float]):
    pass

#fp = save_png_of_network("C:\\Users\\jrrm5\\Desktop\\Eldredge\\PG-sims\\Github\\results\\hoffman\\results\\job12236817.1_dsu200_rho100_a72.final.atoms")
fp = ".\\test.png"
unfiltered_pores = pizza_boy(fp);
filtered_pores = disregard_pores_based_on_area_criteria(unfiltered_pores, 10, None);