from collections import deque
from dataclasses import dataclass
from import_data_from_dumps import import_2D_triclinic_box_bounds_from_dump, import_atoms_from_dump, import_bonds_from_dump, reconstruct_molecule_objects
from lammps_PG_objects import Atom, Bond, Angle, GlycanMolecule, minimum_image_displacement_2d
from os.path import splitext
import os.path
from simulation_constants_settings import DSU
import numpy as np
import re

import matplotlib.pyplot as plt
from matplotlib.image import imread


@dataclass(frozen=True)
class PoreImageMetrics:
    """Pixel-derived pore observables for one declared periodic raster.

    These values describe the complement of a rendered bond image. They are
    not chemical connectivity or a resolution-independent geometric pore
    ground truth. ``cell_area`` and ``pore_areas`` use the squared units of the
    input coordinates.
    """

    pixel_shape: tuple[int, int]
    cell_area: float
    pixel_area: float
    line_width_pixels: int
    occupied_pixel_count: int
    occupied_fraction: float
    pore_pixel_counts: tuple[int, ...]
    pore_areas: tuple[float, ...]


def _validated_cell(triclinic_bounds):
    try:
        xlo, xhi, xy, ylo, yhi = (float(value) for value in triclinic_bounds)
    except (TypeError, ValueError) as exc:
        raise ValueError("triclinic_bounds must contain five finite values") from exc
    values = np.array([xlo, xhi, xy, ylo, yhi], dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("triclinic_bounds must contain five finite values")
    if xhi <= xlo or yhi <= ylo:
        raise ValueError("periodic cell lengths must be positive")
    cell = np.array([[xhi - xlo, xy], [0.0, yhi - ylo]], dtype=float)
    return np.array([xlo, ylo], dtype=float), cell


def _validated_raster_parameters(image_shape, line_width_pixels):
    try:
        rows, columns = image_shape
    except (TypeError, ValueError) as exc:
        raise ValueError("image_shape must be a two-integer (rows, columns) tuple") from exc
    if (
        isinstance(rows, bool)
        or isinstance(columns, bool)
        or not isinstance(rows, (int, np.integer))
        or not isinstance(columns, (int, np.integer))
        or rows <= 0
        or columns <= 0
    ):
        raise ValueError("image_shape must contain two positive integers")
    if (
        isinstance(line_width_pixels, bool)
        or not isinstance(line_width_pixels, (int, np.integer))
        or line_width_pixels <= 0
    ):
        raise ValueError("line_width_pixels must be a positive integer")
    return int(rows), int(columns), int(line_width_pixels)


def chemical_connected_components(atoms, bonds):
    """Return components of the declared chemical bond graph.

    Geometry, rendered intersections, and pixel adjacency are deliberately
    ignored. Every atom is included, including isolated atoms. Missing bond
    endpoints are rejected rather than silently manufacturing or dropping
    connectivity.
    """

    atom_ids = set(atoms)
    for atom_id, atom in atoms.items():
        if type(atom_id) is not int or atom.id != atom_id:
            raise ValueError("atom keys must be persistent integer atom IDs")

    adjacency = {atom_id: set() for atom_id in atom_ids}
    for bond in bonds.values():
        for endpoint in (bond.atom_id_1, bond.atom_id_2):
            if endpoint not in adjacency:
                raise ValueError(
                    f"bond {bond.id} references unknown atom ID {endpoint}"
                )
        adjacency[bond.atom_id_1].add(bond.atom_id_2)
        adjacency[bond.atom_id_2].add(bond.atom_id_1)

    components = []
    unvisited = set(atom_ids)
    while unvisited:
        seed = min(unvisited)
        component = set()
        queue = [seed]
        while queue:
            atom_id = queue.pop()
            if atom_id not in unvisited:
                continue
            unvisited.remove(atom_id)
            component.add(atom_id)
            queue.extend(adjacency[atom_id] & unvisited)
        components.append(frozenset(component))
    components.sort(key=lambda component: min(component))
    return tuple(components)


def rasterize_periodic_network(
    atoms,
    bonds,
    triclinic_bounds,
    *,
    image_shape,
    line_width_pixels=1,
):
    """Rasterize declared bonds on a periodic restricted-triclinic cell.

    Array rows follow the second lattice coordinate and columns the first.
    Each bond follows its exact 2D minimum image and is painted with a declared
    square pixel brush. The returned mask is a visual observable only;
    coincident painted pixels do not alter chemical topology.
    """

    rows, columns, line_width_pixels = _validated_raster_parameters(
        image_shape, line_width_pixels
    )
    origin, cell = _validated_cell(triclinic_bounds)
    inverse_cell = np.linalg.inv(cell)
    chemical_connected_components(atoms, bonds)  # validates endpoint identity
    occupied = np.zeros((rows, columns), dtype=bool)
    first_offset = -(line_width_pixels // 2)
    paint_offsets = [
        (row_offset, column_offset)
        for row_offset in range(first_offset, first_offset + line_width_pixels)
        for column_offset in range(first_offset, first_offset + line_width_pixels)
    ]

    for bond in bonds.values():
        atom_1 = atoms[bond.atom_id_1]
        atom_2 = atoms[bond.atom_id_2]
        start = np.array([atom_1.x, atom_1.y], dtype=float)
        if not np.all(np.isfinite(start)):
            raise ValueError(f"bond {bond.id} has nonfinite endpoint coordinates")
        displacement, _ = minimum_image_displacement_2d(
            atom_1, atom_2, triclinic_bounds
        )
        if not np.all(np.isfinite(displacement)):
            raise ValueError(f"bond {bond.id} has nonfinite endpoint coordinates")
        start_fractional = inverse_cell @ (start - origin)
        displacement_fractional = inverse_cell @ displacement
        displacement_pixels = displacement_fractional * np.array(
            [columns, rows], dtype=float
        )
        sample_count = max(
            2, int(np.ceil(4.0 * np.max(np.abs(displacement_pixels)))) + 1
        )
        for progress in np.linspace(0.0, 1.0, sample_count):
            fractional = (start_fractional + progress * displacement_fractional) % 1.0
            column = int(np.floor(fractional[0] * columns)) % columns
            row = int(np.floor(fractional[1] * rows)) % rows
            for row_offset, column_offset in paint_offsets:
                occupied[
                    (row + row_offset) % rows,
                    (column + column_offset) % columns,
                ] = True
    return occupied


def periodic_pore_components(boolean_image_data):
    """Label four-neighbor components of unoccupied pixels on a 2D torus."""

    occupied = np.asarray(boolean_image_data, dtype=bool)
    if occupied.ndim != 2 or 0 in occupied.shape:
        raise ValueError("periodic pore masks must be nonempty and two-dimensional")
    rows, columns = occupied.shape
    unclaimed = set(map(tuple, np.argwhere(~occupied)))
    pores = []
    while unclaimed:
        seed = min(unclaimed)
        component = set()
        queue = deque([seed])
        unclaimed.remove(seed)
        while queue:
            row, column = queue.popleft()
            component.add((row, column))
            neighbors = (
                ((row - 1) % rows, column),
                ((row + 1) % rows, column),
                (row, (column - 1) % columns),
                (row, (column + 1) % columns),
            )
            for neighbor in neighbors:
                if neighbor in unclaimed:
                    unclaimed.remove(neighbor)
                    queue.append(neighbor)
        pores.append(frozenset(component))
    pores.sort(key=lambda pore: (-len(pore), min(pore)))
    return tuple(pores)


def analyze_periodic_pore_mask(
    boolean_image_data, *, cell_area, line_width_pixels
):
    """Measure periodic image-complement components with explicit pixel scale."""

    occupied = np.asarray(boolean_image_data, dtype=bool)
    _, _, line_width_pixels = _validated_raster_parameters(
        occupied.shape, line_width_pixels
    )
    cell_area = float(cell_area)
    if not np.isfinite(cell_area) or cell_area <= 0.0:
        raise ValueError("cell_area must be positive and finite")
    pores = periodic_pore_components(occupied)
    pixel_area = cell_area / occupied.size
    counts = tuple(len(pore) for pore in pores)
    return PoreImageMetrics(
        pixel_shape=occupied.shape,
        cell_area=cell_area,
        pixel_area=pixel_area,
        line_width_pixels=line_width_pixels,
        occupied_pixel_count=int(np.count_nonzero(occupied)),
        occupied_fraction=float(np.mean(occupied)),
        pore_pixel_counts=counts,
        pore_areas=tuple(count * pixel_area for count in counts),
    )


def analyze_periodic_network_image(
    atoms,
    bonds,
    triclinic_bounds,
    *,
    image_shape,
    line_width_pixels=1,
):
    """Rasterize and measure image pores under one declared raster setting."""

    _, cell = _validated_cell(triclinic_bounds)
    occupied = rasterize_periodic_network(
        atoms,
        bonds,
        triclinic_bounds,
        image_shape=image_shape,
        line_width_pixels=line_width_pixels,
    )
    return analyze_periodic_pore_mask(
        occupied,
        cell_area=float(cell[0, 0] * cell[1, 1]),
        line_width_pixels=line_width_pixels,
    )


def save_monochrome_png_of_network(
    atoms,
    bonds,
    triclinic_bounds,
    save_to_filepath,
    *,
    pixels_per_DSU=1.0,
    line_width_pixels=2,
):
    print(f"Exporting monochrome network image to file: {save_to_filepath}")
    origin, cell = _validated_cell(triclinic_bounds)
    del origin
    pixels_per_DSU = float(pixels_per_DSU)
    if not np.isfinite(pixels_per_DSU) or pixels_per_DSU <= 0.0:
        raise ValueError("pixels_per_DSU must be positive and finite")
    columns = max(1, int(np.ceil(cell[0, 0] / DSU * pixels_per_DSU)))
    rows = max(1, int(np.ceil(cell[1, 1] / DSU * pixels_per_DSU)))
    occupied = rasterize_periodic_network(
        atoms,
        bonds,
        triclinic_bounds,
        image_shape=(rows, columns),
        line_width_pixels=line_width_pixels,
    )
    image = np.where(occupied, 0.0, 1.0)
    plt.imsave(
        save_to_filepath,
        image,
        cmap="gray",
        vmin=0.0,
        vmax=1.0,
        origin="lower",
    )
    print(
        f"Saved image to {save_to_filepath}. Resolution: "
        f"{columns / (cell[0, 0] / DSU)}, {rows / (cell[1, 1] / DSU)} px / DSU; "
        f"line width: {line_width_pixels} px"
    )
    return save_to_filepath

def pizza_boy(filename, disregard_tail_of_fraction = 0.01) -> list[set[tuple[int,int]]]:
    image_data = imread(filename);
    boolean_image_data = bool_me(image_data);
    gossamer, unclaimed = establish_gossamer_and_unclaimed_sets(boolean_image_data)
    print(len(gossamer), len(unclaimed))

    disregard_tail_of_fraction = float(disregard_tail_of_fraction)
    if (
        not np.isfinite(disregard_tail_of_fraction)
        or disregard_tail_of_fraction < 0.0
        or disregard_tail_of_fraction >= 1.0
    ):
        raise ValueError("disregard_tail_of_fraction must be in [0, 1)")
    pores = list(periodic_pore_components(boolean_image_data))
    cutoff = len(unclaimed) * disregard_tail_of_fraction
    discarded_pixels = 0
    while pores and discarded_pixels + len(pores[-1]) <= cutoff:
        discarded_pixels += len(pores.pop())
    print(
        f"Found {len(pores)} periodic image pores; discarded "
        f"{discarded_pixels} pixels from the smallest-component tail"
    )
    return [set(pore) for pore in pores]

def bool_me(img_data : np.typing.NDArray):
    """Convert grayscale/RGB/RGBA image data to an occupied-pixel mask.

    Opaque non-white pixels are occupied. Transparent pixels are background.
    Integer images are normalized by their dtype maximum; floating images must
    already use the conventional [0, 1] image range.
    """

    image = np.asarray(img_data)
    if image.ndim not in (2, 3) or 0 in image.shape[:2]:
        raise ValueError("image data must be a nonempty grayscale, RGB, or RGBA array")
    if np.issubdtype(image.dtype, np.integer):
        image = image.astype(float) / np.iinfo(image.dtype).max
    else:
        image = image.astype(float)
    if not np.all(np.isfinite(image)) or np.any((image < 0.0) | (image > 1.0)):
        raise ValueError("image intensities must be finite and within [0, 1]")

    if image.ndim == 2:
        intensity = image
        alpha = np.ones_like(intensity)
    else:
        channels = image.shape[2]
        if channels == 1:
            intensity = image[:, :, 0]
            alpha = np.ones_like(intensity)
        elif channels == 2:
            intensity = image[:, :, 0]
            alpha = image[:, :, 1]
        elif channels in (3, 4):
            intensity = np.mean(image[:, :, :3], axis=2)
            alpha = image[:, :, 3] if channels == 4 else np.ones(image.shape[:2])
        else:
            raise ValueError("image data must have one to four channels")
    return (alpha > 1e-12) & (intensity < 1.0 - 1e-12)

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

def flood_fill_PBC_less_recursion(pixels_in_pore : set[tuple[int,int]], r0 : tuple[int,int], boolean_image_data : np.typing.NDArray) -> set[tuple[int,int]]:
    """Compatibility wrapper around the bounded iterative periodic fill."""

    occupied = np.asarray(boolean_image_data, dtype=bool)
    if occupied.ndim != 2 or 0 in occupied.shape:
        raise ValueError("periodic pore masks must be nonempty and two-dimensional")
    rows, columns = occupied.shape
    try:
        row, column = r0
    except (TypeError, ValueError) as exc:
        raise ValueError("r0 must be a two-index pixel") from exc
    if not (0 <= row < rows and 0 <= column < columns):
        raise ValueError("r0 is outside the image")
    if occupied[row, column]:
        raise ValueError("r0 must identify an unoccupied pore pixel")
    queue = deque([(row, column)])
    pixels_in_pore.add((row, column))
    while queue:
        current_row, current_column = queue.popleft()
        for neighbor in (
            ((current_row - 1) % rows, current_column),
            ((current_row + 1) % rows, current_column),
            (current_row, (current_column - 1) % columns),
            (current_row, (current_column + 1) % columns),
        ):
            if neighbor not in pixels_in_pore and not occupied[neighbor]:
                pixels_in_pore.add(neighbor)
                queue.append(neighbor)
    return pixels_in_pore

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
    if xDSU <= 0:
        raise ValueError("x cell length must be positive")
    if img_data.ndim not in (2, 3):
        raise ValueError("image must be a grayscale, RGB, or RGBA array")
    xPX = np.shape(img_data)[1];

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
