import sys
import os
import unittest

sys.path.append(os.path.join(os.path.curdir,"..","src"))

from simulation_constants_settings import PEPTIDE_COEFFICIENTS, E_PEPTIDE_CUTOFF
from lammps_PG_objects import inv_peptide_energy_lammps, peptide_energy_lammps

class test_inv_peptide_energy(unittest.TestCase):
    def test1(self):
        C = E_PEPTIDE_CUTOFF;
        (r1, r2) = inv_peptide_energy_lammps(C);

        V1 = peptide_energy_lammps(r1);
        V2 = peptide_energy_lammps(r2);

        self.assertEqual(C, V1);
        self.assertEqual(C, V2);