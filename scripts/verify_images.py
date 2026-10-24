"""Read-only pixel and delivery-file audit for a set or selected listing images."""
import argparse
from functools import lru_cache
import hashlib
from io import BytesIO
from itertools import product
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

SYNTHETIC_PERFORMER_TAG = 'contains-synthetic-performer'
APLUS_SIZES = {'desktop': (1464, 600), 'mobile': (600, 450)}
DELIVERY_SUFFIXES = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG'}

try:
    from PIL import Image, ImageChops, ImageCms, ImageOps
except ImportError:
    print('Pillow with ImageCms is required; use a verified Python runtime or scripts/verify_images.ps1.', file=sys.stderr)
    raise SystemExit(2)


@lru_cache(maxsize=1)
def srgb_probe():
    """Sample the RGB cube plus full neutral and primary ramps, entirely in memory."""
    levels = [round(index * 255 / 16) for index in range(17)]
    samples = list(product(levels, repeat=3))
    for value in range(256):
        samples.extend(((value, value, value), (value, 0, 0), (0, value, 0), (0, 0, value)))
    probe = Image.new('RGB', (len(samples), 1))
    probe.putdata(samples)
    return probe


@lru_cache(maxsize=32)
def icc_status(profile_bytes):
    """Verify matrix/TRC behavior against sRGB; a description is only a label."""
    try:
        profile = ImageCms.ImageCmsProfile(BytesIO(profile_bytes))
        description = ImageCms.getProfileDescription(profile).strip()
        core = profile.profile
        if core.xcolor_space.strip() != 'RGB':
            return 'non_srgb', description
        # Do not infer equivalence for arbitrary input LUTs from a finite probe.
        if not core.is_matrix_shaper or any(value[0] for value in core.clut.values()):
            return 'unverified', description
        probe = srgb_probe()
        converted = ImageCms.profileToProfile(
            probe, profile, ImageCms.createProfile('sRGB'), outputMode='RGB',
            renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
            flags=ImageCms.Flags.NOOPTIMIZE,
        )
        # Allow one 8-bit code value for normal ICC rounding differences.
        max_difference = max(high for low, high in ImageChops.difference(probe, converted).getextrema())
        return ('srgb' if max_difference <= 1 else 'non_srgb'), description
    except (OSError, ValueError, TypeError, ImageCms.PyCMSError):
        return 'invalid_profile', None


def color_status(image):
    """Check the embedded color definition, not a previous conversion's accuracy."""
    if 'icc_profile' in image.info:
        profile_bytes = image.info['icc_profile']
        return icc_status(profile_bytes) if profile_bytes else ('invalid_profile', None)
    if image.format == 'PNG' and image.info.get('srgb') in (0, 1, 2, 3):
        return 'srgb', 'PNG sRGB chunk'
    return 'unverified', None


def performer_metadata(image, required):
    """Inspect explicit provenance declarations; do not infer AI people from pixels."""
    keywords = image.getexif().get(40094, b'')
    try:
        if not isinstance(keywords, str):
            keywords = bytes(keywords).decode('utf-16le')
        windows_keywords = [part.strip() for part in keywords.rstrip('\x00').split(';') if part.strip()]
    except (TypeError, ValueError, UnicodeError):
        windows_keywords = []
    xmp_keywords = []
    xmp = image.info.get('xmp')
    if xmp:
        try:
            root = ET.fromstring(xmp)
            query = './/{http://purl.org/dc/elements/1.1/}subject/{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag/{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li'
            xmp_keywords = [node.text.strip() for node in root.findall(query) if node.text]
        except (ET.ParseError, ValueError):
            pass
    present = SYNTHETIC_PERFORMER_TAG in windows_keywords and SYNTHETIC_PERFORMER_TAG in xmp_keywords
    return {'required': required, 'windows_keywords': windows_keywords, 'xmp_dc_subject': xmp_keywords,
            'passed': present if required else None}


def audit(paths, category, expected_count=7, synthetic_performer_paths=None, aplus_layout=None):
    if category not in ('fashion', 'other'):
        raise ValueError('category must be fashion or other')
    if aplus_layout is not None and aplus_layout not in APLUS_SIZES:
        raise ValueError('aplus_layout must be desktop, mobile or None')
    if not isinstance(expected_count, int) or isinstance(expected_count, bool) or expected_count < 1:
        raise ValueError('expected_count must be a positive integer')
    paths = list(paths)
    required_paths = {Path(item).resolve() for item in (synthetic_performer_paths or [])}
    if not required_paths.issubset({Path(item).resolve() for item in paths}):
        raise ValueError('Synthetic-performer targets must be included in the current image audit')
    errors = []
    rows = []
    seen = set()
    seen_pixels = set()
    if len(paths) != expected_count:
        errors.append(f'Expected {expected_count} images; received {len(paths)}')
    for item in paths:
        path = Path(item)
        pixel_errors = []
        delivery_errors = []
        row = {'path': str(path.resolve())}
        try:
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen:
                delivery_errors.append('Duplicate image file content')
            seen.add(digest)
            with Image.open(BytesIO(data)) as image:
                fmt = image.format
                image.load()
                status, profile_description = color_status(image)
                performer = performer_metadata(image, path.resolve() in required_paths)
                displayed = ImageOps.exif_transpose(image)
                width, height = displayed.size
                # Normalize mode and EXIF orientation; ignore container metadata.
                # Size is part of the key so equal byte streams with different
                # row shapes cannot be mistaken for the same displayed image.
                pixel_digest = hashlib.sha256(displayed.convert('RGBA').tobytes()).hexdigest()
                pixel_key = (width, height, pixel_digest)
                if pixel_key in seen_pixels:
                    delivery_errors.append('Duplicate decoded image pixels')
                seen_pixels.add(pixel_key)
                transparent = False
                if 'A' in displayed.getbands():
                    transparent = displayed.getchannel('A').getextrema()[0] < 255
                elif 'transparency' in image.info:
                    transparent = displayed.convert('RGBA').getchannel('A').getextrema()[0] < 255
                row.update(width=width, height=height, format=fmt, mode=displayed.mode,
                           color_status=status, color_profile=profile_description,
                           has_transparency=transparent, synthetic_performer=performer,
                           file_size_bytes=len(data), dpi=image.info.get('dpi'))
                if aplus_layout:
                    target = APLUS_SIZES[aplus_layout]
                    if (width, height) != target:
                        pixel_errors.append(f'A+ {aplus_layout} export must be exactly {target[0]}x{target[1]}px (user delivery target)')
                    if len(data) >= 2_000_000:
                        delivery_errors.append('A+ final file must be under 2,000,000 bytes')
                    dpi = image.info.get('dpi')
                    valid_dpi = isinstance(dpi, (tuple, list)) and len(dpi) == 2
                    if valid_dpi:
                        valid_dpi = all(isinstance(value, (int, float)) and math.isfinite(value) and value >= 72 for value in dpi)
                    if not valid_dpi:
                        delivery_errors.append('A+ export must declare at least 72 DPI in both directions')
                else:
                    if min(width, height) <= 2000:
                        pixel_errors.append('Shortest side must be strictly greater than 2000px')
                    if category == 'fashion' and height <= width:
                        pixel_errors.append('Fashion image must be portrait')
                    if category == 'other' and width != height:
                        pixel_errors.append('Non-fashion image must be square')
                if fmt not in ('JPEG', 'PNG'):
                    delivery_errors.append('Delivery format must be JPEG or PNG')
                expected_format = DELIVERY_SUFFIXES.get(path.suffix.lower())
                if expected_format is None:
                    delivery_errors.append('Delivery filename extension must be .jpg, .jpeg or .png')
                elif fmt != expected_format:
                    delivery_errors.append(f'Filename extension {path.suffix} does not match decoded format {fmt}')
                if displayed.mode not in ('RGB', 'RGBA', 'P'):
                    delivery_errors.append('Delivery color mode must be RGB-compatible; CMYK/grayscale are not accepted')
                if status != 'srgb':
                    delivery_errors.append(f'sRGB declaration not verified: {status}')
                if transparent:
                    delivery_errors.append('Final listing image must not contain transparent pixels')
                if getattr(image, 'is_animated', False):
                    delivery_errors.append('Animated images are not final listing stills')
                if performer['required'] and not performer['passed']:
                    delivery_errors.append('AI-person image requires exact contains-synthetic-performer in Windows Tags (XPKeywords) and XMP dc:subject rdf:Bag')
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            message = f'Cannot read image: {exc}'
            pixel_errors.append(message)
            delivery_errors.append(message)
        row.update(pixel_passed=not pixel_errors, delivery_passed=not delivery_errors,
                   pixel_errors=pixel_errors, delivery_errors=delivery_errors,
                   errors=pixel_errors + delivery_errors)
        rows.append(row)
    pixel_passed = bool(rows) and all(row['pixel_passed'] for row in rows)
    delivery_passed = not errors and bool(rows) and all(row['delivery_passed'] for row in rows)
    return {
        'passed': pixel_passed and delivery_passed,
        'pixel_passed': pixel_passed, 'delivery_passed': delivery_passed,
        'category': category, 'expected_count': expected_count, 'actual_count': len(paths),
        'profile': 'aplus' if aplus_layout else 'gallery', 'aplus_layout': aplus_layout,
        'errors': errors, 'images': rows,
        'scope': 'File checks only. ICC behavior is sampled against sRGB; this does not prove prior color-conversion accuracy. Pixel deduplication detects exact decoded matches, not similar compositions. Product truth, white background, faces, text, IP and platform rules require visual review.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--category', choices=('fashion', 'other'), required=True)
    parser.add_argument('--expected-count', type=int, default=7,
                        help='7 for a complete set; number of selected images for single/revision tasks')
    parser.add_argument('--synthetic-performer', action='append', default=[], type=Path,
                        help='AI-person image requiring metadata; repeat for each applicable file')
    parser.add_argument('--aplus-layout', choices=tuple(APLUS_SIZES),
                        help='Use the fixed A+ desktop/mobile export contract instead of gallery dimensions')
    parser.add_argument('images', nargs='+', type=Path)
    args = parser.parse_args()
    if args.expected_count < 1:
        parser.error('--expected-count must be positive')
    try:
        report = audit(args.images, args.category, args.expected_count, args.synthetic_performer, args.aplus_layout)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
