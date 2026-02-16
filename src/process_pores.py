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

def pizza_boy(filename):
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
       newest_freshness_pore = flood_fill_PBC(whatever_pixel_idc, boolean_image_data);
       pores.append(newest_freshness_pore)
       [unclaimed.remove(bro) for bro in newest_freshness_pore]

    # That you're a Pizza Boy
    return pores
    

def bool_me(img_data : np.typing.NDArray):
    nx, ny, nz = np.shape(img_data);

    flat_img_data = np.array((nx,ny),dtype=bool);
    flat_img_data = (img_data[:,:,2] == 0) # True if Black

    return flat_img_data;

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

def flood_fill_PBC(r0 : tuple[int,int], boolean_image_data : np.typing.NDArray) -> set[tuple[int,int]]:
    pass
            

#fp = save_png_of_network("C:\\Users\\jrrm5\\Desktop\\Eldredge\\PG-sims\\Github\\results\\hoffman\\results\\job12236817.1_dsu200_rho100_a72.final.atoms")
fp = ".\\test.png"
how_could_i_know_that(fp)