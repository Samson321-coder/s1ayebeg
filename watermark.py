"""
watermark.py — Adds a text watermark to house listing photos.
"""
from io import BytesIO
import math
from PIL import Image, ImageDraw, ImageFont

WATERMARK_TEXT = "@AkerayTekerayBot"

def apply_watermark(image_bytes: bytes) -> BytesIO:
    """
    Takes raw image bytes, draws a watermark in the bottom-right corner,
    and returns the result as a BytesIO object ready for Telegram upload.
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    width, height = img.size

    # Create a transparent overlay layer
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to load a font, fall back to default if not available
    font_size = max(20, width // 25)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        try:
            # Try common Linux path
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

    # Measure text size
    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Position: bottom-right with padding
    padding = 15
    x = width - text_width - padding
    y = height - text_height - padding

    # Draw shadow for readability
    draw.text((x + 2, y + 2), WATERMARK_TEXT, font=font, fill=(0, 0, 0, 160))
    # Draw the main text in white
    draw.text((x, y), WATERMARK_TEXT, font=font, fill=(255, 255, 255, 220))

    # Merge overlay with original
    watermarked = Image.alpha_composite(img, overlay).convert("RGB")

    output = BytesIO()
    watermarked.save(output, format="JPEG", quality=92)
    output.seek(0)
    return output


def create_collage(image_bytes_list, max_size=1600, margin=10):
    """Create a single JPEG collage from multiple photos."""
    if not image_bytes_list:
        raise ValueError("No images provided for collage")
    if len(image_bytes_list) == 1:
        return BytesIO(image_bytes_list[0]) if isinstance(image_bytes_list[0], (bytes, bytearray)) else image_bytes_list[0]

    images = [Image.open(BytesIO(img_bytes)).convert("RGB") for img_bytes in image_bytes_list]
    count = len(images)
    cols = int(math.ceil(math.sqrt(count)))
    rows = int(math.ceil(count / cols))

    cell_size = (max_size - margin * (cols + 1)) // cols
    collage_width = cols * cell_size + margin * (cols + 1)
    collage_height = rows * cell_size + margin * (rows + 1)

    collage = Image.new("RGB", (collage_width, collage_height), color=(255, 255, 255))

    for idx, img in enumerate(images):
        img.thumbnail((cell_size, cell_size), Image.LANCZOS)
        col = idx % cols
        row = idx // cols
        x = margin + col * (cell_size + margin) + (cell_size - img.width) // 2
        y = margin + row * (cell_size + margin) + (cell_size - img.height) // 2
        collage.paste(img, (x, y))

    output = BytesIO()
    collage.save(output, format="JPEG", quality=85)
    output.seek(0)
    return output
