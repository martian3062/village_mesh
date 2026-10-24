"""Check that remote job packaging cannot sweep local assets or credentials."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import build_kaggle_policy_job as bundle


class KaggleBundleTests(unittest.TestCase):
    def test_remote_job_excludes_unlisted_files_and_is_private(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / 'Scripts'
            scripts.mkdir()
            for name in bundle.FILES:
                (scripts / name).write_text('pass\n')
            (scripts / 'unrelated_secret.py').write_text('DO_NOT_UPLOAD_PRIVATE_VALUE')
            (root / 'access_token').write_text('DO_NOT_UPLOAD_PRIVATE_VALUE')
            (root / 'Content').mkdir()
            (root / 'Content/character.uasset').write_text('DO_NOT_UPLOAD_EPIC_ASSET')
            with patch.object(bundle, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                bundle.build('exampleuser')
            code = (root / 'Saved/Kaggle/job/village_mesh_gpu.py').read_text()
            self.assertNotIn('DO_NOT_UPLOAD', code)
            compile(code, '<bundle>', 'exec')
            metadata = json.loads((root / 'Saved/Kaggle/job/kernel-metadata.json').read_text())
            self.assertIs(metadata['is_private'], True)
            self.assertEqual(metadata['dataset_sources'], [])

    def test_rejects_invalid_owner_before_writing(self):
        for owner in ('../other', 'user/other-kernel', 'user\nother'):
            with self.assertRaises(ValueError):
                bundle.build(owner)


if __name__ == '__main__':
    unittest.main()
