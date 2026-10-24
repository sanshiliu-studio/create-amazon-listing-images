"""A+ upload files have their own dimensions, size and DPI requirements."""
from io import BytesIO, StringIO
import contextlib
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

from PIL import Image, ImageCms

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'verify_images.py'
AUDIT = runpy.run_path(str(SCRIPT))['audit']


def fixture(size=(1464, 600), dpi=(72, 72)):
    output = BytesIO()
    options = {'icc_profile': ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()}
    if dpi is not None:
        options['dpi'] = dpi
    Image.new('RGB', size, (30, 100, 140)).save(output, format='JPEG', **options)
    return output.getvalue()


class AplusTests(unittest.TestCase):
    def check(self, data=None, layout='desktop', **kwargs):
        with patch.object(Path, 'read_bytes', return_value=fixture() if data is None else data):
            return AUDIT(['aplus.jpg'], 'fashion', expected_count=1, aplus_layout=layout, **kwargs)

    def test_desktop_uses_aplus_spec_instead_of_gallery_short_side(self):
        self.assertTrue(self.check()['passed'])

    def test_mobile_uses_600_by_450_even_for_fashion(self):
        self.assertTrue(self.check(fixture((600, 450)), layout='mobile')['passed'])

    def test_mobile_file_cannot_pass_as_desktop(self):
        self.assertFalse(self.check(fixture((600, 450)))['pixel_passed'])

    def test_export_requires_exact_selected_dimensions(self):
        self.assertFalse(self.check(fixture((2928, 1200)))['pixel_passed'])

    def test_gallery_requirements_are_unchanged(self):
        with patch.object(Path, 'read_bytes', return_value=fixture()):
            report = AUDIT(['aplus.jpg'], 'other', expected_count=1)
        self.assertFalse(report['pixel_passed'])

    def test_missing_dpi_does_not_pass_delivery(self):
        report = self.check(fixture(dpi=None))
        self.assertTrue(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])

    def test_dpi_below_72_is_rejected(self):
        self.assertFalse(self.check(fixture(dpi=(71, 72)))['delivery_passed'])

    def test_file_at_two_million_bytes_is_rejected(self):
        data = fixture()
        data += b'\x00' * (2_000_000 - len(data))
        report = self.check(data)
        self.assertTrue(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])

    def test_ai_person_marker_is_still_required(self):
        report = self.check(synthetic_performer_paths=['aplus.jpg'])
        self.assertTrue(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])

    def test_unknown_layout_is_not_silently_treated_as_gallery(self):
        with self.assertRaises(ValueError):
            self.check(layout='unknown')

    def test_cli_accepts_aplus_layout(self):
        output = StringIO()
        with patch.object(Path, 'read_bytes', return_value=fixture()), patch.object(sys, 'argv', [str(SCRIPT), '--category', 'other', '--expected-count', '1', '--aplus-layout', 'desktop', 'aplus.jpg']), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                runpy.run_path(str(SCRIPT), run_name='__main__')
        self.assertEqual(result.exception.code, 0)


if __name__ == '__main__':
    unittest.main()
