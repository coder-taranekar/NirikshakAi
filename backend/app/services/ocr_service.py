"""
OCR Service — image preprocessing, text extraction, and font height estimation.

Processing pipeline:
  1. Preprocess image (deskew, denoise, normalise) via OpenCV + Pillow
  2. Extract DPI from image metadata (EXIF or default 150 dpi)
  3. Run Google Cloud Vision API (primary, if API key is configured)
  4. Fall back to EasyOCR (English + Hindi) if GCV is unavailable or fails
  5. Convert pixel bounding-box heights → estimated physical mm heights
     using image DPI, for font-size compliance checks (Rules 7/8)

OCR result structure returned by this service:
{
  "raw_text": "...",
  "blocks": [
    {
      "text": "MRP ₹45.00",
      "bounding_box": {"x": 10, "y": 200, "width": 80, "height": 12},
      "confidence": 0.98,
      "estimated_font_height_mm": 2.3
    }
  ],
  "image_dpi": 150,
  "image_width_px": 1200,
  "image_height_px": 800,
  "ocr_engine": "gcv" | "easyocr"
}
"""

import io
import logging
from typing import Any

import cv2
import numpy as np
from PIL import Image, ExifTags

from app.config import settings

logger = logging.getLogger(__name__)

# Default DPI assumed when image has no DPI metadata (common for camera photos)
_DEFAULT_DPI = 150
_MM_PER_INCH = 25.4


# ── Image Preprocessing ────────────────────────────────────────────────────────

def _pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Convert a PIL Image (RGB) to a BGR OpenCV ndarray."""
    return cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2BGR)


def _cv2_to_pil(cv2_img: np.ndarray) -> Image.Image:
    """Convert a BGR OpenCV ndarray to a PIL Image (RGB)."""
    return Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB))


def _deskew(cv2_img: np.ndarray) -> np.ndarray:
    """
    Detect and correct skew using the Hough line transform.
    If skew is < 0.5 degrees, the original image is returned unchanged
    to avoid unnecessary resampling noise.
    """
    gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 10:
        return cv2_img
    angle = cv2.minAreaRect(coords)[-1]
    # minAreaRect returns angles in [-90, 0); normalise to [-45, 45)
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5:
        return cv2_img
    h, w = cv2_img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        cv2_img, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


def _denoise_and_sharpen(cv2_img: np.ndarray) -> np.ndarray:
    """
    Apply a mild denoise followed by an unsharp mask to improve OCR accuracy
    on blurry or low-contrast label images.
    """
    denoised = cv2.fastNlMeansDenoisingColored(cv2_img, None, 6, 6, 7, 21)
    blurred = cv2.GaussianBlur(denoised, (0, 0), 3)
    sharpened = cv2.addWeighted(denoised, 1.5, blurred, -0.5, 0)
    return sharpened


def preprocess_image(image_bytes: bytes) -> tuple[Image.Image, int]:
    """
    Load, deskew, denoise, and sharpen the input image.

    Returns:
      - processed PIL Image (RGB, ready for OCR)
      - dpi: int (from EXIF if available, else _DEFAULT_DPI)
    """
    pil_img = Image.open(io.BytesIO(image_bytes))

    # Extract DPI from EXIF
    dpi = _DEFAULT_DPI
    try:
        exif_data = pil_img._getexif()  # type: ignore[attr-defined]
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, "")
                if tag == "XResolution":
                    raw = value
                    dpi = int(raw[0] / raw[1]) if isinstance(raw, tuple) else int(raw)
                    dpi = max(72, min(dpi, 1200))  # clamp to sane range
                    break
    except Exception:
        pass  # EXIF not available — use default DPI

    cv2_img = _pil_to_cv2(pil_img)
    cv2_img = _deskew(cv2_img)
    cv2_img = _denoise_and_sharpen(cv2_img)
    processed = _cv2_to_pil(cv2_img)

    return processed, dpi


# ── Font Height Estimation ─────────────────────────────────────────────────────

def pixels_to_mm(pixels: float, dpi: int) -> float:
    """
    Convert a pixel measurement to millimetres using the image DPI.

    Formula: mm = (pixels / dpi) × 25.4
    """
    return round((pixels / dpi) * _MM_PER_INCH, 2)


# ── Google Cloud Vision API ────────────────────────────────────────────────────

def _run_gcv(pil_img: Image.Image) -> list[dict[str, Any]]:
    """
    Run Google Cloud Vision TEXT_DETECTION on the image.
    Returns a list of block dicts with text, bounding_box, confidence.
    Raises RuntimeError if the API call fails.
    """
    from google.cloud import vision  # type: ignore
    from google.oauth2.credentials import Credentials  # type: ignore

    # Build image bytes
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    content = buf.getvalue()

    client = vision.ImageAnnotatorClient(
        credentials=Credentials(token=settings.google_cloud_vision_api_key)
        if settings.google_cloud_vision_api_key
        else None
    )
    image = vision.Image(content=content)
    response = client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"GCV error: {response.error.message}")

    blocks: list[dict[str, Any]] = []
    for annotation in response.text_annotations[1:]:  # skip index 0 = full text
        verts = annotation.bounding_poly.vertices
        xs = [v.x for v in verts]
        ys = [v.y for v in verts]
        x = min(xs)
        y = min(ys)
        width = max(xs) - x
        height = max(ys) - y
        blocks.append({
            "text": annotation.description,
            "bounding_box": {"x": x, "y": y, "width": width, "height": height},
            "confidence": float(annotation.confidence) if hasattr(annotation, "confidence") else 0.95,
        })

    return blocks


# ── EasyOCR Fallback ───────────────────────────────────────────────────────────

_easyocr_reader = None  # lazy-load — model download is slow


def _get_easyocr_reader():
    """Lazily initialise the EasyOCR reader (en + hi) on first call."""
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr  # type: ignore
        _easyocr_reader = easyocr.Reader(["en", "hi"], gpu=False, verbose=False)
    return _easyocr_reader


def _run_easyocr(pil_img: Image.Image) -> list[dict[str, Any]]:
    """
    Run EasyOCR on the image as a fallback.
    Returns the same block-dict format as _run_gcv.
    """
    reader = _get_easyocr_reader()
    cv2_img = _pil_to_cv2(pil_img)
    results = reader.readtext(cv2_img, detail=1, paragraph=False)

    blocks: list[dict[str, Any]] = []
    for bbox, text, confidence in results:
        # EasyOCR bbox: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        x = int(min(xs))
        y = int(min(ys))
        width = int(max(xs) - x)
        height = int(max(ys) - y)
        blocks.append({
            "text": text,
            "bounding_box": {"x": x, "y": y, "width": width, "height": height},
            "confidence": float(confidence),
        })

    return blocks


# ── Main Entry Point ───────────────────────────────────────────────────────────

def run_ocr(image_bytes: bytes) -> dict[str, Any]:
    """
    Full OCR pipeline: preprocess → extract text → estimate font heights.

    Returns the structured OCR result dict (stored in Inspection.ocr_result).
    Always succeeds — if all engines fail, returns a result with empty blocks
    and an error key so the compliance engine can handle gracefully.
    """
    processed_img, dpi = preprocess_image(image_bytes)
    width_px, height_px = processed_img.size

    # Try GCV first (if API key is configured)
    blocks: list[dict[str, Any]] = []
    engine_used = "none"
    error_msg: str | None = None

    if settings.google_cloud_vision_api_key:
        try:
            blocks = _run_gcv(processed_img)
            engine_used = "gcv"
            logger.info("ocr_gcv_success", block_count=len(blocks))
        except Exception as exc:
            logger.warning("ocr_gcv_failed", error=str(exc))
            error_msg = str(exc)

    # Fall back to EasyOCR
    if engine_used == "none":
        try:
            blocks = _run_easyocr(processed_img)
            engine_used = "easyocr"
            logger.info("ocr_easyocr_success", block_count=len(blocks))
        except Exception as exc:
            logger.error("ocr_easyocr_failed", error=str(exc))
            error_msg = str(exc)

    # Augment blocks with physical font height estimates
    for block in blocks:
        bb = block["bounding_box"]
        block["estimated_font_height_mm"] = pixels_to_mm(bb["height"], dpi)

    raw_text = " ".join(b["text"] for b in blocks)

    result: dict[str, Any] = {
        "raw_text": raw_text,
        "blocks": blocks,
        "image_dpi": dpi,
        "image_width_px": width_px,
        "image_height_px": height_px,
        "ocr_engine": engine_used,
    }
    if error_msg:
        result["ocr_error"] = error_msg

    return result
