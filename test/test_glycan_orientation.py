import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__),"..","src"))

from simulation_constants_settings import PEPTIDE_COEFFICIENTS, E_PEPTIDE_CUTOFF
from numpy import deg2rad
from lammps_PG_objects import *
from assemble_pg_network import add_simple_glycan

XLO = -50;
XHI = 50;
XY = 0;
YLO = -50;
YHI = 50;
BOUNDS = (XLO, XHI, XY, YLO, YHI);
ANGLES = np.linspace(-85,85,10)

class test_glycan_orientation(unittest.TestCase):

    # Non-Periodic
    def test1(self):
        for ANGLE in ANGLES:
            atoms = dict();
            bonds = dict();
            angles = dict();
            glycans = dict();

            add_simple_glycan(atoms, bonds, angles, glycans, 0, 0, 20);

            g : GlycanMolecule = glycans[1];
            g.rotate_wrt_cm(atoms, deg2rad(ANGLE));
            g.correct_orthogonal_PCB(atoms, BOUNDS[0], BOUNDS[1], BOUNDS[3], BOUNDS[4])

            a_calculated = g.get_orientation_with_respect_to_hoop(atoms, BOUNDS);
            self.assertAlmostEqual(ANGLE, a_calculated, 5);

    # Periodic in x
    def test2(self):
        for ANGLE in ANGLES:
            atoms = dict();
            bonds = dict();
            angles = dict();
            glycans = dict();

            add_simple_glycan(atoms, bonds, angles, glycans, 45, 0, 20);

            g : GlycanMolecule = glycans[1];
            g.rotate_wrt_cm(atoms, deg2rad(ANGLE));
            g.correct_orthogonal_PCB(atoms, XLO, XHI, YLO, YHI)

            a_calculated = g.get_orientation_with_respect_to_hoop(atoms, BOUNDS);
            self.assertAlmostEqual(ANGLE, a_calculated, 5);

    # Periodic in y
    def test3(self):
        for ANGLE in ANGLES:
            atoms = dict();
            bonds = dict();
            angles = dict();
            glycans = dict();

            add_simple_glycan(atoms, bonds, angles, glycans, 0, 45, 20);

            g : GlycanMolecule = glycans[1];
            g.rotate_wrt_cm(atoms, deg2rad(ANGLE));
            g.correct_orthogonal_PCB(atoms, XLO, XHI, YLO, YHI)

            a_calculated = g.get_orientation_with_respect_to_hoop(atoms, BOUNDS);
            self.assertAlmostEqual(ANGLE, a_calculated, 5);

    # Periodic in both x & y
    def test4(self):
        for ANGLE in ANGLES:
            atoms = dict();
            bonds = dict();
            angles = dict();
            glycans = dict();

            add_simple_glycan(atoms, bonds, angles, glycans, 45, 45, 20);

            g : GlycanMolecule = glycans[1];
            g.rotate_wrt_cm(atoms, deg2rad(ANGLE));
            g.correct_orthogonal_PCB(atoms, XLO, XHI, YLO, YHI)

            a_calculated = g.get_orientation_with_respect_to_hoop(atoms, BOUNDS);
            self.assertAlmostEqual(ANGLE, a_calculated, 5);