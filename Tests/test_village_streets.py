import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
import village_streets as streets


class StreetTests(unittest.TestCase):
    def test_source_surface_takes_precedence(self):
        self.assertEqual(streets.surface_for(dict(id=3,kind='residential',surface='asphalt')),'asphalt')
        self.assertEqual(streets.surface_for(dict(id=4,kind='unclassified',surface='unpaved')),'dirt')
    def test_classification_preserves_connector_and_field_routes(self):
        for kind in ('primary','secondary','tertiary','unclassified'):
            self.assertEqual(streets.surface_for(dict(id=3,kind=kind)),'asphalt')
        for kind in ('track','path','footway'):
            self.assertEqual(streets.surface_for(dict(id=4,kind=kind)),'dirt')
        self.assertEqual({streets.surface_for(dict(id=i,kind='residential')) for i in range(9)},{'brick','pavers'})
    def test_clipping_retains_crossing_and_rejects_outside(self):
        self.assertEqual(streets.clipped_segment([-90000,0],[90000,0]),([-63000.,0.],[63000.,0.]))
        self.assertIsNone(streets.clipped_segment([-90000,70000],[90000,70000]))
        self.assertIsNone(streets.clipped_segment([70000,-10],[70000,10]))
    def test_joint_cross_sections_are_finite_and_bounded(self):
        for points in ([[0,0],[100,0],[100,100]],[[0,0],[100,0],[1,1]],[[0,0],[100,0],[200,0]]):
            for i in range(len(points)):
                n=streets.cross_section(points,i)
                self.assertTrue(all(math.isfinite(x) for x in n));self.assertLessEqual(math.hypot(*n),1.500001)
        self.assertEqual(streets.cross_section([[0,0],[100,0],[200,0]],1),(0.,1.))
