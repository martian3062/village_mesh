"""Protect the existing resident roster and local-only output boundary."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
from metahuman_pilot_config import read_profile


class MetaHumanPilotTests(unittest.TestCase):
    def check_profile(self, profile):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'profile.json'
            path.write_text(json.dumps(profile))
            return read_profile(path)

    def test_pilot_is_separate_from_existing_people(self):
        profile = read_profile()
        people = json.loads((ROOT / 'Assets/NPC/personas.json').read_text())['people']
        self.assertNotIn(profile['id'], {p['id'] for p in people})
        self.assertIsNone(profile['resident_id'])
        self.assertEqual(profile['integration'], 'isolated_pilot')

    def test_asset_outputs_cannot_overwrite_village_assets(self):
        profile = copy.deepcopy(read_profile())
        for key in ('character_asset', 'assembly_root'):
            invalid = copy.deepcopy(profile)
            invalid[key] = '/Game/VillageMeshV3/Characters'
            with self.assertRaises(ValueError):
                self.check_profile(invalid)

    def test_wardrobe_paths_require_reviewed_sources(self):
        profile = copy.deepcopy(read_profile())
        profile['wardrobe']['Hair'] = '/Game/UnreviewedDownload/Hair'
        with self.assertRaises(ValueError):
            self.check_profile(profile)


if __name__ == '__main__':
    unittest.main()
