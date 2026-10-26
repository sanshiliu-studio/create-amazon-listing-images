"""Exercise real Pillow decoding; keep fixture bytes in memory to avoid file cleanup."""
import contextlib
import builtins
from functools import lru_cache
from io import BytesIO, StringIO
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import zlib

from PIL import Image, ImageCms, PngImagePlugin


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'verify_images.py'
AUDIT = runpy.run_path(str(SCRIPT))['audit']
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()


def image_bytes(image, fmt='PNG', **options):
    output = BytesIO()
    image.save(output, format=fmt, icc_profile=options.pop('icc_profile', SRGB), **options)
    return output.getvalue()


def changed_profile(tag, relative_offset, value):
    """Change a real ICC tag without replacing it with an unreadable fixture."""
    profile = bytearray(SRGB)
    count = int.from_bytes(profile[128:132], 'big')
    for index in range(count):
        entry = 132 + 12 * index
        if profile[entry:entry + 4] == tag:
            offset = int.from_bytes(profile[entry + 4:entry + 8], 'big') + relative_offset
            profile[offset:offset + len(value)] = value
            return bytes(profile)
    raise AssertionError(f'Missing ICC fixture tag: {tag!r}')


@lru_cache(maxsize=24)
def fixtures(size=(2048, 2048), mode='RGB', fmt='PNG', profile='srgb', alpha=255):
    payloads = {}
    for index in range(7):
        color = (index * 20, 40, 60)
        if mode == 'RGBA':
            color += (alpha,)
        elif mode == 'CMYK':
            color += (0,)
        elif mode == 'P':
            color = index
        image = Image.new(mode, size, color)
        options = {}
        if profile == 'srgb':
            options['icc_profile'] = SRGB
        elif profile == 'broken':
            options['icc_profile'] = b'not-an-icc-profile'
        elif profile == 'png-chunk':
            info = PngImagePlugin.PngInfo()
            info.add(b'sRGB', b'\x00')
            options['pnginfo'] = info
        if mode == 'P':
            options['transparency'] = index
        output = BytesIO()
        image.save(output, format=fmt, **options)
        payloads[f'image-{index}.{fmt.lower()}'] = output.getvalue()
    return payloads


@contextlib.contextmanager
def image_files(payloads):
    original_open = Image.open

    def read_bytes(path):
        try:
            return payloads[path.name]
        except KeyError:
            raise FileNotFoundError(str(path)) from None

    def open_image(path):
        if hasattr(path, 'read'):
            return original_open(path)
        return original_open(BytesIO(read_bytes(Path(path))))

    with patch.object(Path, 'read_bytes', read_bytes), patch.object(Image, 'open', open_image):
        yield list(payloads)


class AuditTests(unittest.TestCase):
    def check_images(self, payloads=None, category='other', **kwargs):
        with image_files(fixtures() if payloads is None else payloads) as paths:
            return AUDIT(paths, category, **kwargs)

    def test_seven_srgb_images_pass_both_checks(self):
        report = self.check_images()
        self.assertTrue(report['passed'])
        self.assertTrue(report['pixel_passed'])
        self.assertTrue(report['delivery_passed'])

    def test_single_image_uses_requested_count(self):
        one = dict(list(fixtures().items())[:1])
        report = self.check_images(one, expected_count=1)
        self.assertTrue(report['passed'])
        self.assertEqual(report['expected_count'], 1)

    def test_partial_revision_uses_requested_count(self):
        two = dict(list(fixtures().items())[:2])
        self.assertTrue(self.check_images(two, expected_count=2)['passed'])

    def test_incomplete_set_keeps_pixel_and_count_results_separate(self):
        one = dict(list(fixtures().items())[:1])
        report = self.check_images(one)
        self.assertFalse(report['passed'])
        self.assertTrue(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])
        self.assertTrue(report['errors'])

    def test_2000_is_rejected_without_failing_delivery_format(self):
        report = self.check_images(fixtures(size=(2000, 2000)))
        self.assertFalse(report['passed'])
        self.assertFalse(report['pixel_passed'])
        self.assertTrue(report['delivery_passed'])

    def test_accepted_native_portrait_keeps_actual_pixels(self):
        report = self.check_images(fixtures(size=(1086, 1448)), category='fashion', gallery_resolution='native')
        self.assertTrue(report['passed'])
        self.assertEqual(report['gallery_resolution'], 'native')
        self.assertEqual((report['images'][0]['width'], report['images'][0]['height']), (1086, 1448))

    def test_native_gallery_keeps_format_and_color_requirements(self):
        report = self.check_images(fixtures(size=(1086, 1448), mode='CMYK', fmt='JPEG', profile='none'),
                                   category='fashion', gallery_resolution='native')
        self.assertTrue(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])

    def test_native_gallery_keeps_category_aspect_requirement(self):
        report = self.check_images(fixtures(size=(1086, 1448)), category='other', gallery_resolution='native')
        self.assertFalse(report['pixel_passed'])

    def test_native_gallery_does_not_relax_aplus_size(self):
        report = self.check_images(fixtures(size=(1086, 1448)), aplus_layout='desktop', gallery_resolution='native')
        self.assertFalse(report['pixel_passed'])

    def test_gallery_resolution_rejects_unknown_policy(self):
        with self.assertRaises(ValueError):
            self.check_images(gallery_resolution='unknown')

    def test_fashion_must_be_portrait(self):
        self.assertFalse(self.check_images(category='fashion')['passed'])
        self.assertTrue(self.check_images(fixtures(size=(2048, 2731)), category='fashion')['passed'])

    def test_cmyk_jpeg_is_not_accepted_as_srgb(self):
        report = self.check_images(fixtures(mode='CMYK', fmt='JPEG', profile='none'))
        self.assertFalse(report['passed'])
        self.assertTrue(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])

    def test_rgb_without_color_profile_is_unverified(self):
        report = self.check_images(fixtures(profile='none'))
        self.assertFalse(report['passed'])
        self.assertFalse(report['delivery_passed'])
        self.assertEqual(report['images'][0]['color_status'], 'unverified')

    def test_corrupt_profile_cannot_pass(self):
        self.assertFalse(self.check_images(fixtures(profile='broken'))['passed'])

    def test_srgb_name_cannot_hide_different_primaries(self):
        profile = changed_profile(b'rXYZ', 8, round(0.70 * 65536).to_bytes(4, 'big'))
        self.assertIn('sRGB', ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(BytesIO(profile))))
        renamed = profile.replace('sRGB built-in'.encode('utf-16be'), 'Not sRGB data'.encode('utf-16be'))
        for candidate in (profile, renamed):
            with self.subTest(description=ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(BytesIO(candidate))).strip()):
                data = image_bytes(Image.new('RGB', (2048, 2048)), icc_profile=candidate)
                report = self.check_images({'custom.png': data}, expected_count=1)
                self.assertTrue(report['pixel_passed'])
                self.assertFalse(report['delivery_passed'])

    def test_srgb_name_cannot_hide_different_tone_curve(self):
        profile = changed_profile(b'rTRC', 12, round(1.8 * 65536).to_bytes(4, 'big'))
        data = image_bytes(Image.new('RGB', (2048, 2048)), icc_profile=profile)
        self.assertFalse(self.check_images({'gamma.png': data}, expected_count=1)['passed'])

    def test_equivalent_srgb_profile_does_not_need_srgb_in_its_name(self):
        profile = SRGB.replace('sRGB built-in'.encode('utf-16be'), 'RGB reference'.encode('utf-16be'))
        self.assertNotIn('sRGB', ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(BytesIO(profile))))
        data = image_bytes(Image.new('RGB', (2048, 2048)), icc_profile=profile)
        self.assertTrue(self.check_images({'alias.png': data}, expected_count=1)['passed'])

    def test_corrupt_icc_cannot_be_hidden_by_png_srgb_chunk(self):
        # A real corrupt iCCP chunk decodes to icc_profile=None in Pillow.
        payloads = {}
        iccp = b'iCCP' + b'Bad\x00\x00not-zlib'
        chunk = (len(iccp) - 4).to_bytes(4, 'big') + iccp + zlib.crc32(iccp).to_bytes(4, 'big')
        for name, data in fixtures(profile='png-chunk').items():
            payloads[name] = data[:33] + chunk + data[33:]
        report = self.check_images(payloads)
        self.assertFalse(report['passed'])
        self.assertEqual(report['images'][0]['color_status'], 'invalid_profile')

    def test_transparent_rgba_is_not_a_final_listing_image(self):
        report = self.check_images(fixtures(mode='RGBA', alpha=100))
        self.assertFalse(report['delivery_passed'])
        self.assertTrue(report['images'][0]['has_transparency'])

    def test_opaque_alpha_channel_is_accepted(self):
        report = self.check_images(fixtures(mode='RGBA'))
        self.assertTrue(report['passed'])
        self.assertFalse(report['images'][0]['has_transparency'])

    def test_palette_transparency_is_detected(self):
        report = self.check_images(fixtures(mode='P'))
        self.assertFalse(report['passed'])
        self.assertTrue(report['images'][0]['has_transparency'])

    def test_png_srgb_chunk_is_accepted(self):
        self.assertTrue(self.check_images(fixtures(profile='png-chunk'))['passed'])

    def test_unsupported_delivery_format_is_rejected(self):
        report = self.check_images(fixtures(fmt='BMP', profile='none'))
        self.assertFalse(report['passed'])
        self.assertTrue(report['pixel_passed'])

    def test_png_renamed_to_jpg_is_rejected(self):
        report = self.check_images({'renamed.jpg': next(iter(fixtures().values()))}, expected_count=1)
        self.assertTrue(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])

    def test_jpeg_renamed_to_png_is_rejected(self):
        data = next(iter(fixtures(fmt='JPEG').values()))
        self.assertFalse(self.check_images({'renamed.png': data}, expected_count=1)['passed'])

    def test_supported_suffixes_are_case_insensitive(self):
        png = next(iter(fixtures().values()))
        jpeg = next(iter(fixtures(fmt='JPEG').values()))
        for name, data in [('one.PNG', png), ('one.JPG', jpeg), ('one.JPEG', jpeg)]:
            with self.subTest(name=name):
                self.assertTrue(self.check_images({name: data}, expected_count=1)['passed'])

    def test_unsupported_suffix_is_rejected_even_for_valid_png(self):
        self.assertFalse(self.check_images({'one.dat': next(iter(fixtures().values()))}, expected_count=1)['passed'])

    def test_duplicates_cannot_fill_out_a_set(self):
        payloads = dict(fixtures())
        names = list(payloads)
        payloads[names[1]] = payloads[names[0]]
        self.assertFalse(self.check_images(payloads)['passed'])

    def test_same_pixels_with_different_comments_are_duplicates(self):
        image = Image.new('RGB', (2048, 2048), (10, 50, 80))
        payloads = {}
        for text in ('first', 'second'):
            info = PngImagePlugin.PngInfo()
            info.add_text('Comment', text)
            payloads[text + '.png'] = image_bytes(image, pnginfo=info)
        self.assertNotEqual(*payloads.values())
        report = self.check_images(payloads, expected_count=2)
        self.assertTrue(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])
        self.assertIn('Duplicate decoded image pixels', report['images'][1]['delivery_errors'])

    def test_same_pixels_across_jpeg_and_png_are_duplicates(self):
        jpeg = image_bytes(Image.new('RGB', (2048, 2048), (10, 50, 80)), fmt='JPEG')
        with Image.open(BytesIO(jpeg)) as decoded:
            png = image_bytes(decoded.convert('RGBA'))
        report = self.check_images({'one.jpg': jpeg, 'two.png': png}, expected_count=2)
        self.assertFalse(report['delivery_passed'])
        self.assertIn('Duplicate decoded image pixels', report['images'][1]['delivery_errors'])

    def test_pixel_duplicates_follow_exif_display_orientation(self):
        image = Image.new('RGB', (2048, 2048), (10, 50, 80))
        image.putpixel((0, 0), (255, 0, 0))
        exif = Image.Exif()
        exif[274] = 6
        payloads = {'one.png': image_bytes(image),
                    'two.png': image_bytes(image.transpose(Image.Transpose.ROTATE_90), exif=exif)}
        report = self.check_images(payloads, expected_count=2)
        self.assertFalse(report['delivery_passed'])
        self.assertIn('Duplicate decoded image pixels', report['images'][1]['delivery_errors'])

    def test_unreadable_image_is_reported(self):
        report = self.check_images({'broken.png': b'not an image'}, expected_count=1)
        self.assertFalse(report['passed'])
        self.assertFalse(report['pixel_passed'])
        self.assertFalse(report['delivery_passed'])

    def test_empty_input_never_passes(self):
        self.assertFalse(self.check_images({})['passed'])

    def test_expected_count_must_be_positive(self):
        with self.assertRaises(ValueError):
            self.check_images(expected_count=0)

    def test_cli_accepts_count_and_emits_json(self):
        one = dict(list(fixtures().items())[:1])
        with image_files(one) as paths, patch.object(sys, 'argv', [str(SCRIPT), '--category', 'other', '--expected-count', '1', *paths]):
            output = StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as result:
                runpy.run_path(str(SCRIPT), run_name='__main__')
        self.assertEqual(result.exception.code, 0)
        self.assertTrue(json.loads(output.getvalue())['passed'])


@unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell'), 'PowerShell is unavailable')
class LauncherTests(unittest.TestCase):
    def launch(self, *args, shell=None):
        shell = shell or shutil.which('pwsh') or shutil.which('powershell')
        return subprocess.run(
            [shell, '-NoProfile', '-NonInteractive', '-File', str(SCRIPT.with_suffix('.ps1')), *args],
            capture_output=True, encoding='utf-8', timeout=20,
        )

    def test_explicit_working_python_is_actually_probed(self):
        result = self.launch('-CheckEnvironment', '-PythonPath', sys.executable)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(Path(report['python']).resolve(), Path(sys.executable).resolve())
        self.assertTrue(report['pillow'])

    def test_invalid_explicit_python_does_not_fall_back_silently(self):
        result = self.launch('-CheckEnvironment', '-PythonPath', str(SCRIPT.parent / 'nonexistent-python.exe'))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(result.stdout.strip())
        self.assertIn('No working Python', result.stderr)

    def test_missing_images_returns_actionable_error(self):
        result = self.launch('-PythonPath', sys.executable)
        self.assertEqual(result.returncode, 2)
        self.assertIn('image paths', result.stderr)

    @unittest.skipUnless(shutil.which('powershell'), 'Windows PowerShell is unavailable')
    def test_windows_powershell_legacy_argument_passing(self):
        result = self.launch('-CheckEnvironment', '-PythonPath', sys.executable,
                             shell=shutil.which('powershell'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'ready')


class EnvironmentTests(unittest.TestCase):
    def test_direct_entry_reports_dependency_failure_as_exit_two(self):
        real_import = builtins.__import__

        def without_pillow(name, *args, **kwargs):
            if name == 'PIL':
                raise ImportError('Pillow unavailable')
            return real_import(name, *args, **kwargs)

        error = StringIO()
        with patch.object(builtins, '__import__', without_pillow), contextlib.redirect_stderr(error):
            with self.assertRaises(SystemExit) as result:
                runpy.run_path(str(SCRIPT), run_name='__main__')
        self.assertEqual(result.exception.code, 2)
        self.assertIn('Pillow', error.getvalue())


if __name__ == '__main__':
    unittest.main()
