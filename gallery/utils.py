from PIL import Image
import pytesseract
import io
import re
from datetime import datetime

def extract_timestamp_from_watermark(image_path):
    image_path = '/home/psci/projects/Django_Workspace/all_sky_gallery/media/all_sky_images/2020/03/01/wat_ma1_20-03-01_23-18-01-61.jpg'
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})", text)
        if match:
            return datetime.strptime(match.group(0), "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None

def generate_thumbnail_bytes(image_path, size=(128, 128)):
    with Image.open(image_path) as img:
        img.thumbnail(size)
        byte_io = io.BytesIO()
        img.save(byte_io, format='JPEG', quality=40)
        return byte_io.getvalue()