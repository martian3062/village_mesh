"""Cross-data regressions: source preservation, occupied land and map bounds."""
import json,math,sys,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Scripts'))
import v3_layout as layout
import v3_geometry as geometry

class FullVillageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=json.loads((ROOT/'Assets/World/v3_world.json').read_text())

    def test_mapped_footprints_and_ids_preserved(self):
        source={b['id']:b for b in layout.BUILDINGS}
        self.assertEqual(set(source),{b['id'] for b in self.plan['buildings']})
        for b in self.plan['buildings']:
            self.assertEqual(b['points'],[list(p) for p in source[b['id']]['points']])

    def test_every_requested_use_has_a_distinct_site(self):
        self.assertEqual({p['kind'] for p in self.plan['landmarks']},
                         {'mandir','gurdwara','school','playground','market','dairy','tower','telecom','farm'})
        self.assertEqual(len({tuple(p['center_cm']) for p in self.plan['landmarks']}),9)

    def test_authored_sites_do_not_obstruct_mapped_roads_or_houses(self):
        occupied=[layout.bbox(b['points']) for b in layout.BUILDINGS];sites=[]
        for p in self.plan['landmarks']+self.plan['fields']:
            x,y,_=p['center_cm'];w,d=p['size_cm'];r=layout.rect(x,y,w,d)
            self.assertFalse(layout.road_intersects(r),p['id'])
            self.assertFalse(any(layout.overlap(r,b) for b in occupied+sites),p['id'])
            self.assertLess(max(abs(v) for v in r),64000)
            sites.append(r)

    def test_style_variety_is_not_only_colour(self):
        self.assertEqual(set(layout.STYLES),{b['style'] for b in self.plan['buildings']})
        shape=dict(id='test',points=[[-600,-500],[600,-500],[600,500],[-600,500]],
                   center=[0,0],height=660,seed=3062,palette=0,pilot=False)
        signatures=[]
        for style in layout.STYLES:
            g=geometry.Geometry();geometry.house(g,dict(**shape,style=style))
            triangles=sorted(tuple(tuple(obj.vertices[i-1]) for i in face) for obj in g.groups.values() for face in obj.faces)
            signatures.append(hashlib.sha256(repr(triangles).encode()).hexdigest())
        self.assertEqual(len(set(signatures)),8)

    def test_every_inferred_site_is_labelled(self):
        occupied=[layout.bbox(b['points']) for b in layout.BUILDINGS]
        for p in self.plan['landmarks']:
            self.assertIn('representative',p['location_confidence'])
            self.assertIn('unverified',p['architecture_confidence'])
            self.assertEqual(p['arrival_cm'][2],100)
            x,y,_=p['arrival_cm']
            self.assertFalse(any(layout.overlap(layout.rect(x,y,150,150),b) for b in occupied),p['id'])

    def test_no_nonfinite_geometry(self):
        g=geometry.Geometry()
        for p in self.plan['landmarks']:geometry.landmark(g,p)
        for obj in g.groups.values():
            self.assertTrue(all(math.isfinite(c) for v in obj.vertices for c in v))
            self.assertTrue(all(1<=i<=len(obj.vertices) for f in obj.faces for i in f))

    def test_vertical_walls_have_nondegenerate_texture_coordinates(self):
        for triangle in [[(0,0,0),(500,0,0),(500,0,330)],[(0,0,0),(0,500,0),(0,500,330)],[(0,0,0),(500,0,0),(500,500,0)]]:
            a,b,c=geometry.face_uvs(triangle)
            determinant=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1])
            self.assertGreater(abs(determinant),.1)

    def test_veranda_posts_respect_full_road_width(self):
        # Deliberately place a candidate on a real centreline; a whole column
        # pair must be omitted rather than obstructing a lane.
        a,b,width=layout.base.SEGMENTS[0]
        midpoint=((a[0]+b[0])/2,(a[1]+b[1])/2,0)
        self.assertEqual(geometry.clear_veranda_posts([midpoint,(midpoint[0]+100,midpoint[1],0)]),[])
        self.assertEqual(len(geometry.clear_veranda_posts([(900000,900000,0),(900100,900000,0)])),2)

if __name__=='__main__':unittest.main()
