"""Keep asset publication scoped and reject missing LFS payloads."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import lfs_publication as publication


class LFSPublicationTests(unittest.TestCase):
    def test_private_unreviewed_and_traversal_paths_rejected(self):
        for path in ('Saved/Kaggle/access_token', 'Content/Village/Unknown.uasset',
                     'Content/VillageMesh/../../secret.uasset', 'Content/VillageMesh/secret.env',
                     'Assets/Downloaded/unpinned.jpg', 'C:/secret.uasset'):
            with self.subTest(path=path):
                self.assertFalse(publication.approved_path(path))

    def test_pointer_or_changed_payload_cannot_pass_as_real_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = 'Content/VillageMesh/Example.uasset'
            asset = root / relative
            asset.parent.mkdir(parents=True)
            payload = b'authored asset test payload'
            asset.write_bytes(payload)
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'files': [{'path': relative, 'bytes': len(payload),
                'sha256': hashlib.sha256(payload).hexdigest()}], 'file_count': 1, 'total_bytes': len(payload)}))
            with patch.object(publication, 'MANIFEST', manifest):
                publication.verify(root)
                asset.write_bytes(b'version https://git-lfs.github.com/spec/v1\n')
                with self.assertRaises(ValueError):
                    publication.verify(root)
                asset.write_bytes(b'x' * len(payload))
                with self.assertRaises(ValueError):
                    publication.verify(root)


if __name__ == '__main__':
    unittest.main()
