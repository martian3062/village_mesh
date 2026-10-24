"""Prevent report refreshes from overwriting the single guide or licence notices."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from readme_sections import export_notices, export_package_readme, update_report


class ReadmeSectionsTests(unittest.TestCase):
    def test_report_replacement_preserves_other_sections_and_roots_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'README.md'
            prefix = '# Guide\n<!-- BEGIN:v2-results -->'
            suffix = '<!-- END:v2-results -->\n<!-- BEGIN:third-party-notices -->\nKeep attribution.\n<!-- END:third-party-notices -->\n'
            path.write_text(prefix + '\nold results\n' + suffix)
            update_report('v2-results', '# Result\n\n[Evidence](evidence.json)\n\n## Limits\nCurrent.', 'Docs/V2', root)
            result = path.read_text()
            self.assertTrue(result.startswith(prefix))
            self.assertTrue(result.endswith(suffix))
            self.assertIn('(Docs/V2/evidence.json)', result)
            self.assertIn('### Limits', result)
            self.assertIn('id="v2-results-limits"', result)
            self.assertNotIn('old results', result)
            output = root / 'package/THIRD_PARTY_NOTICES.txt'
            export_notices(output, root)
            self.assertIn('Keep attribution.', output.read_text())
            path.write_text(result + '\n![Preview](Docs/V2/daylight.png)\n[Section](#v2-results)\n')
            export_package_readme(root/'package/README.md', root)
            packaged = (root/'package/README.md').read_text()
            self.assertIn('https://raw.githubusercontent.com/martian3062/village_mesh/main/Docs/V2/daylight.png', packaged)
            self.assertIn('https://github.com/martian3062/village_mesh/blob/main/Docs/V2/evidence.json', packaged)
            self.assertIn('[Section](#v2-results)', packaged)

    def test_missing_or_duplicate_markers_leave_readme_unchanged(self):
        for content in ('# Guide\n', '<!-- BEGIN:v2-results -->x<!-- BEGIN:v2-results --><!-- END:v2-results -->'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / 'README.md'
                path.write_text(content)
                with self.assertRaises(ValueError):
                    update_report('v2-results', '# New', 'Docs/V2', root)
                self.assertEqual(path.read_text(), content)
