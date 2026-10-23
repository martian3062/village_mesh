import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Scripts"))
import world_layout
import export_well_wind as wind
import h5py
import numpy as np


class WorldToolsTests(unittest.TestCase):
    def test_terrain_preserves_level_village_and_has_valid_faces(self):
        for x, y, *_ in world_layout.house_plots():
            self.assertEqual(world_layout.height(x, y), 0.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "terrain.obj"
            world_layout.write_terrain(path, cells=8)
            lines = path.read_text().splitlines()
            self.assertEqual(sum(line.startswith("v ") for line in lines), 81)
            faces = [line.split()[1:] for line in lines if line.startswith("f ")]
            self.assertEqual(len(faces), 128)
            self.assertTrue(all(1 <= int(v.split("/")[0]) <= 81 for face in faces for v in face))

    def test_well_axis_order_sampling_loop_and_invalid_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            with h5py.File(Path(tmp) / "fixture.h5", "w") as handle:
                values = np.zeros((2, 6, 3, 4, 2))
                values[1, :, 2, 3, 0] = np.arange(1, 7)
                values[1, :, 2, 3, 1] = 2.0
                ds = handle.create_dataset("t1_fields/velocity", data=values)
                ds.attrs.update(sample_varying=True, time_varying=True, dim_varying=[True, True])
                handle.create_dataset("dimensions/time", data=np.arange(6) * 0.1)
                t, v = wind.point_trace(handle, 1, (2, 3), 3)
                np.testing.assert_array_equal(v[:, 0], [1, 3, 6])
                times, vectors, peak = wind.normalize_trace(t, v, 120)
                self.assertEqual(times[0], 0)
                self.assertEqual(times[-1], 120)
                np.testing.assert_array_equal(vectors[0], vectors[-1])
                self.assertAlmostEqual(np.linalg.norm(vectors, axis=1).max(), 1)
                with self.assertRaises(ValueError):
                    wind.point_trace(handle, 1, (3, 3), 3)
                ds[1, 0, 2, 3, 0] = np.nan
                with self.assertRaises(ValueError):
                    wind.point_trace(handle, 1, (2, 3), 3)

    def test_zero_field_rejected(self):
        with self.assertRaises(ValueError):
            wind.normalize_trace(np.array([0., 1.]), np.zeros((2, 2)))

    def test_published_wind_matches_provenance(self):
        path = ROOT / "Content/Well/wind.csv"
        metadata = json.loads(path.with_suffix(".source.json").read_text())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), metadata["csv_sha256"])


if __name__ == "__main__":
    unittest.main()
