"""Image processing for TV upload: cropping and auto-matte."""
import io
import os
from PIL import Image

TARGET_RATIO = 16 / 9  # Samsung Frame TV aspect ratio
DEFAULT_MATTE_PERCENT = int(os.environ.get("DEFAULT_MATTE_PERCENT", "10"))
TV_MAX_WIDTH = 3840
TV_MAX_HEIGHT = 2160


def process_for_tv(
    image_data: bytes,
    crop_percent: int = 0,
    matte_percent: int = None,
    reframe_enabled: bool = False,
    reframe_offset_x: float = 0.5,
    reframe_offset_y: float = 0.5,
    reframe_zoom: float = 1.0,
) -> bytes:
    """
    Process image for TV display:
    - If reframe_enabled: Scale/crop to fill 16:9 exactly
    - Otherwise: Crop edges, then add matte for 16:9

    Args:
        image_data: Raw image bytes (JPEG/PNG)
        crop_percent: Percentage to crop from each edge (0-50)
        matte_percent: Minimum matte as % of longer side (default from env)
        reframe_enabled: If True, fill frame completely (no matte)
        reframe_offset_x: Horizontal crop position (0.0-1.0)
        reframe_offset_y: Vertical crop position (0.0-1.0)

    Returns:
        PNG bytes ready for TV upload
    """
    if matte_percent is None:
        matte_percent = DEFAULT_MATTE_PERCENT

    # Load image
    img = Image.open(io.BytesIO(image_data))

    # Convert to RGB if necessary (handle RGBA, palette, etc.)
    if img.mode in ('RGBA', 'P', 'LA'):
        # Create white background for transparency
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    if reframe_enabled:
        # Reframe mode: fill 16:9 completely
        img = _reframe_image(img, reframe_offset_x, reframe_offset_y, reframe_zoom)
    else:
        # Standard mode: crop then matte
        if crop_percent > 0:
            img = _crop_image(img, crop_percent)
        img = _add_matte(img, matte_percent)

    # Cap to TV native resolution — sending more pixels gains nothing and slows upload
    if img.width > TV_MAX_WIDTH or img.height > TV_MAX_HEIGHT:
        img = img.resize((TV_MAX_WIDTH, TV_MAX_HEIGHT), Image.Resampling.LANCZOS)

    # JPEG is 3-5x smaller than PNG for photographic content, visually identical on TV
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=92, subsampling=0)
    return output.getvalue()


def _crop_image(img: Image.Image, crop_percent: int) -> Image.Image:
    """Crop percentage from all 4 edges."""
    w, h = img.size
    crop_x = int(w * crop_percent / 100)
    crop_y = int(h * crop_percent / 100)

    left = crop_x
    top = crop_y
    right = w - crop_x
    bottom = h - crop_y

    return img.crop((left, top, right, bottom))


def _reframe_image(
    img: Image.Image,
    offset_x: float = 0.5,
    offset_y: float = 0.5,
    zoom: float = 1.0,
) -> Image.Image:
    """
    Scale and crop image to fill 16:9 frame exactly.

    zoom > 1.0 crops a proportionally smaller area (zooms in), enabling full
    X+Y freedom regardless of the image's own aspect ratio.
    """
    offset_x = max(0.0, min(1.0, offset_x))
    offset_y = max(0.0, min(1.0, offset_y))
    zoom = max(1.0, min(10.0, zoom))

    w, h = img.size
    current_ratio = w / h

    # Base crop dimensions at zoom 1.0 (minimum crop to fill 16:9)
    if current_ratio > TARGET_RATIO:
        base_crop_w = int(h * TARGET_RATIO)
        base_crop_h = h
    else:
        base_crop_w = w
        base_crop_h = int(w / TARGET_RATIO)

    # Shrink crop area by zoom factor so the result fills 16:9 after upscaling
    crop_w = max(1, int(base_crop_w / zoom))
    crop_h = max(1, int(base_crop_h / zoom))

    # Clamp to image bounds
    crop_w = min(crop_w, w)
    crop_h = min(crop_h, h)

    # Position crop within image using offsets
    left = int((w - crop_w) * offset_x)
    top = int((h - crop_h) * offset_y)

    return img.crop((left, top, left + crop_w, top + crop_h))


def _add_matte(img: Image.Image, matte_percent: int) -> Image.Image:
    """
    Add white matte padding to achieve 16:9 aspect ratio.

    Rules:
    - Minimum matte = matte_percent of image's longer side (on all sides)
    - Expand as needed to reach 16:9
    - Image centered on white canvas
    """
    w, h = img.size
    longer_side = max(w, h)
    min_matte = int(longer_side * matte_percent / 100)

    # Start with minimum matte on all sides
    canvas_w = w + (min_matte * 2)
    canvas_h = h + (min_matte * 2)

    # Adjust to 16:9
    current_ratio = canvas_w / canvas_h

    if current_ratio < TARGET_RATIO:
        # Too tall - expand width
        canvas_w = int(canvas_h * TARGET_RATIO)
    elif current_ratio > TARGET_RATIO:
        # Too wide - expand height
        canvas_h = int(canvas_w / TARGET_RATIO)

    # Create white canvas and paste image centered
    canvas = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))
    paste_x = (canvas_w - w) // 2
    paste_y = (canvas_h - h) // 2
    canvas.paste(img, (paste_x, paste_y))

    return canvas


def generate_preview(
    image_data: bytes,
    crop_percent: int = 0,
    matte_percent: int = None,
    reframe_enabled: bool = False,
    reframe_offset_x: float = 0.5,
    reframe_offset_y: float = 0.5,
    reframe_zoom: float = 1.0,
) -> tuple[bytes, bytes]:
    """
    Generate preview images for comparison.

    Returns:
        Tuple of (original_thumbnail, processed_thumbnail) as JPEG bytes
    """
    # Original thumbnail
    original = Image.open(io.BytesIO(image_data))
    if original.mode not in ('RGB', 'L'):
        original = original.convert('RGB')
    original.thumbnail((400, 400), Image.Resampling.LANCZOS)

    orig_output = io.BytesIO()
    original.save(orig_output, format='JPEG', quality=85)

    # Processed thumbnail
    processed_full = process_for_tv(
        image_data, crop_percent, matte_percent,
        reframe_enabled, reframe_offset_x, reframe_offset_y, reframe_zoom
    )
    processed = Image.open(io.BytesIO(processed_full))
    processed.thumbnail((400, 400), Image.Resampling.LANCZOS)

    proc_output = io.BytesIO()
    processed.save(proc_output, format='JPEG', quality=85)

    return orig_output.getvalue(), proc_output.getvalue()
