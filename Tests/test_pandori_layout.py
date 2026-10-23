import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
import pandori_layout as site


class PandoriGeometryTests(unittest.TestCase):
    def test_georeference_and_scale(self):
        self.assertEqual(site.project(site.LON, site.LAT), (0, 0))
        east,north=site.project(site.LON+0.001,site.LAT+0.001)
        self.assertAlmostEqual(east/100,94.85,delta=0.2)
        self.assertAlmostEqual(north/100,111.195,delta=0.01)

    def test_every_roof_preserves_footprint_area(self):
        self.assertEqual(len(site.BUILDINGS),821)
        for building in site.BUILDINGS:
            points=building['points']
            area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))/2
            triangles=site.triangulate(points)
            triangle_area=0
            for i,j,k in triangles:
                a,b,c=points[i],points[j],points[k]
                triangle_area+=((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
            self.assertGreater(area,0)
            self.assertAlmostEqual(area,triangle_area,delta=max(0.01,area*1e-7))

    def test_roads_exclude_vegetation_and_provenance_matches(self):
        a,b,_=site.SEGMENTS[0]
        self.assertFalse(site.clear_site((a[0]+b[0])/2,(a[1]+b[1])/2))
        folder=site.ROOT/'Assets/Geodata'
        for filename,checksum in json.loads((folder/'provenance.json').read_text())['files'].items():
            self.assertEqual(hashlib.sha256((folder/filename).read_bytes()).hexdigest(),checksum)


if __name__=='__main__':unittest.main()
