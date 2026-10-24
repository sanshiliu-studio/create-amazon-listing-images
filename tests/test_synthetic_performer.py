"""Metadata checks use encoded fixture bytes; no image files are modified."""
from io import BytesIO
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

from PIL import Image, ImageCms

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'verify_images.py'
AUDIT = runpy.run_path(str(SCRIPT))['audit']
TAG = 'contains-synthetic-performer'


def jpeg(keywords=None, xmp=True):
    image = Image.new('RGB', (2048, 2048), (120, 130, 140))
    exif = Image.Exif()
    if keywords is not None:
        exif[40094] = (keywords + '\x00').encode('utf-16le')
    options = {'exif': exif, 'icc_profile': ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()}
    if xmp:
        options['xmp'] = (f'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:subject><rdf:Bag><rdf:li>{TAG}</rdf:li></rdf:Bag></dc:subject></rdf:Description></rdf:RDF></x:xmpmeta>').encode()
    result = BytesIO()
    image.save(result, 'JPEG', **options)
    return result.getvalue()


class SyntheticPerformerTests(unittest.TestCase):
    def audit(self, data, required=True):
        with patch.object(Path, 'read_bytes', return_value=data):
            return AUDIT(['test.jpg'], 'other', expected_count=1,
                         synthetic_performer_paths=['test.jpg'] if required else [])

    def test_required_metadata_must_exist_in_both_fields(self):
        report = self.audit(jpeg(TAG))
        self.assertTrue(report['passed'])
        self.assertTrue(report['images'][0]['synthetic_performer']['passed'])

    def test_xmp_alone_does_not_satisfy_windows_tags_requirement(self):
        report = self.audit(jpeg())
        self.assertFalse(report['delivery_passed'])
        self.assertTrue(report['pixel_passed'])

    def test_windows_tags_alone_do_not_satisfy_platform_metadata(self):
        self.assertFalse(self.audit(jpeg(TAG, xmp=False))['delivery_passed'])

    def test_marker_must_be_an_exact_keyword(self):
        self.assertFalse(self.audit(jpeg('not-' + TAG))['delivery_passed'])

    def test_existing_keywords_can_coexist_with_marker(self):
        self.assertTrue(self.audit(jpeg('summer; ' + TAG + ';服装'))['passed'])

    def test_product_only_image_does_not_require_marker(self):
        self.assertTrue(self.audit(jpeg(xmp=False), required=False)['passed'])

    def test_target_must_be_in_the_current_audit_scope(self):
        with self.assertRaises(ValueError):
            AUDIT(['test.jpg'], 'other', expected_count=1,
                  synthetic_performer_paths=['different.jpg'])


if __name__ == '__main__':
    unittest.main()
