import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
import v2_data as data
import v2_layout as layout


class V2DataTests(unittest.TestCase):
    def test_v2_background_exports_without_mutating_v1(self):
        original=[(b['id'],b['height']) for b in layout.base.BUILDINGS]
        with tempfile.TemporaryDirectory() as tmp:
            files=layout.generate(Path(tmp))
            self.assertGreater(len(files),200)
            self.assertTrue(all(Path(p).is_file() and Path(p).stat().st_size>0 for p,_,_ in files))
        self.assertEqual(original,[(b['id'],b['height']) for b in layout.base.BUILDINGS])

    def test_stable_identity_and_heights_survive_source_reordering(self):
        features=data.read('Assets/Geodata/pandori_nijjaran.buildings.geojson')['features']
        a=data.normalized_buildings(features,[])
        b=data.normalized_buildings(list(reversed(features)),[])
        self.assertEqual([(x['id'],x['height'],x['material']) for x in a],[(x['id'],x['height'],x['material']) for x in b])
        self.assertEqual(len({x['id'] for x in a}),821)

    def test_reviewed_override_precedence_and_orphan_rejection(self):
        feature=next(f for f in data.read('Assets/Geodata/pandori_nijjaran.buildings.geojson')['features'] if f['id']==layout.BUILDINGS[0]['source_id'])
        feature=copy.deepcopy(feature);feature['properties']['height']=8.1
        identifier=feature['id']
        override=dict(properties=dict(building_id=identifier,height_m=4.2,confidence='measured',reason='Synthetic test fixture only'))
        a=data.normalized_buildings([feature],[override])[0]
        self.assertEqual(a['height'],420)
        self.assertEqual(a['confidence'],'measured')
        self.assertEqual(data.normalized_buildings([feature],[])[0]['height'],810)
        with self.assertRaises(ValueError):data.normalized_buildings([], [override])
        with self.assertRaises(ValueError):data.normalized_buildings([feature], [override,override])

    def test_regeneration_does_not_mutate_authored_inputs(self):
        paths=[data.ROOT/p for p in ('Assets/Geodata/overrides.geojson','Assets/Reference/manifest.json','Assets/Architecture/archetypes.json','Assets/Routes/pilot_street.json')]
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        data.normalized_buildings();data.normalized_buildings()
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})

    def test_pilot_selection_and_reference_coverage(self):
        pilot=layout.PILOT
        self.assertTrue(150<=pilot['length_m']<=250)
        self.assertEqual(len(pilot['frontages']),16)
        self.assertEqual(sum(f['interior'] for f in pilot['frontages']),3)
        references={f['feature_id'] for f in data.read('Assets/Reference/manifest.json')['features']}
        self.assertEqual(references,{f['building_id'] for f in pilot['frontages']})
        self.assertEqual(len(pilot['cameras']),8)
        self.assertFalse(data.read('Assets/Reference/manifest.json')['local_photo_pack_available'])

    def test_all_enterable_approaches_clear_neighboring_footprints(self):
        lookup={b['id']:b for b in layout.BUILDINGS}
        for f in layout.PILOT['frontages']:
            if f['interior']:
                self.assertTrue(data.entrance_clear(lookup[f['building_id']],f['edge_index'],layout.BUILDINGS),f['building_id'])
        # The rejected second-row door must remain rejected, independent of selection.
        rejected=lookup['eda24ace-de4a-4e47-bee4-3a5dd5e8b944']
        edge=next(f['edge_index'] for f in layout.PILOT['frontages'] if f['building_id']==rejected['id'])
        self.assertFalse(data.entrance_clear(rejected,edge,layout.BUILDINGS))

    def test_fixed_camera_targets_are_visible_frontages(self):
        aimed=data.aim_pilot_cameras(copy.deepcopy(layout.PILOT),layout.BUILDINGS)
        for original,camera in zip(layout.PILOT['cameras'],aimed['cameras']):
            self.assertEqual(original['position_cm'],camera['position_cm'])
            self.assertEqual(original['target_building_id'],camera['target_building_id'])

    def test_road_sections_share_vertices_and_have_valid_camber(self):
        road=next(r for r in layout.ROADS if r['id']==layout.PILOT['road_ids'][0])
        asphalt,shoulder,rows=layout.road_surfaces(road['points'],road['width'])
        self.assertEqual(len(asphalt.faces),(len(rows)-1)*4)
        for row in rows:
            self.assertEqual([p[2] for p in row],[0,2.5,6,2.5,0])
        self.assertTrue(all(math.isfinite(c) for v in asphalt.vertices+shoulder.vertices for c in v))
        for face in asphalt.faces:
            a,b,c=(asphalt.vertices[i-1] for i in face)
            area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            self.assertGreater(area,0)


if __name__=='__main__':unittest.main()
