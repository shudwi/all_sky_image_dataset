from PIL import Image
import pytesseract
import io
import re
import os
import tarfile
import tempfile
from datetime import datetime
from .models import AllSkyImage
import shutil
from pathlib import Path
import cv2

DUMMY_DATE = datetime(1900, 1, 1)

def extract_timestamp_from_watermark(image_path):
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
    
def generate_video_thumbnail_bytes(video_path, size=(128, 128)):
    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()
    cap.release()
    if success:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        img.thumbnail(size)
        byte_io = io.BytesIO()
        img.save(byte_io, format='JPEG', quality=40)
        return byte_io.getvalue()
    return None

def process_tar_file(full_tar_path, tar_record, media_root):
    with tempfile.TemporaryDirectory() as temp_extract_path:
        with tarfile.open(full_tar_path) as tar:
            tar.extractall(temp_extract_path)

        for root, _, files in os.walk(temp_extract_path):
            for file in files:
                if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                full_path = os.path.join(root, file)

                # Parse filename timestamp
                filename_timestamp = parse_filename_timestamp(file)
                if not filename_timestamp:
                    continue

                watermark_timestamp = extract_timestamp_from_watermark(full_path)

                dest_rel_path = os.path.join(
                    "all_sky_images",
                    filename_timestamp.strftime("%Y"),
                    filename_timestamp.strftime("%m"),
                    filename_timestamp.strftime("%d"),
                    file,
                )

                dest_full_path = os.path.join(media_root, dest_rel_path)
                os.makedirs(os.path.dirname(dest_full_path), exist_ok=True)
                shutil.copy2(full_path, dest_full_path)

                preview_bytes = generate_thumbnail_bytes(full_path)

                AllSkyImage.objects.create(
                    file=dest_rel_path.replace("\\", "/"),  # Ensure POSIX-style path in DB
                    filename_timestamp=filename_timestamp,
                    watermark_timestamp=watermark_timestamp,
                    timestamp_mismatch=(filename_timestamp != watermark_timestamp),
                    preview=preview_bytes,
                )


# def parse_filename_timestamp(filename):
#     try:
#         parts = filename.split("_")
#         date_part = parts[2]       # e.g., 20-03-01
#         time_part = parts[3].replace("-", ":").split(".")[0]
#         return datetime.strptime(f"{date_part} {time_part}", "%y-%m-%d %H:%M:%S")
#     except (IndexError, ValueError)as e:
#         print(e)
#         return None

def parse_filename_timestamp(filepath):
    try:
        # Only get the filename, not full path
        filename = os.path.basename(filepath)  # e.g., 2024_09_02__21_46_16.jpg
        match = re.search(r"(\d{4})_(\d{2})_(\d{2})__([0-2]\d)_(\d{2})_(\d{2})", filename)
        if match:
            dt_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}:{match.group(5)}:{match.group(6)}"
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print("Error parsing filename timestamp:", e)
    return None

def admin_process_tar_archive(tar_record):
    tar_record.is_processing = True
    tar_record.should_stop = False
    tar_record.last_message = "Started processing..."
    tar_record.save()

    full_tar_path = os.path.join("raw_data/all_sky_dataset", tar_record.file_path)
    if not os.path.exists(full_tar_path):
        return False, "TAR file not found."

    count = 0

    with tempfile.TemporaryDirectory(prefix=f"sky_gallery_extract_{tar_record.id}_") as temp_extract_path:
        try:
            with tarfile.open(full_tar_path) as tar:
                tar.extractall(temp_extract_path)

            for root, _, files in os.walk(temp_extract_path):
                for file in files:
                    print(file)
                    print(tar_record.should_stop)
                    if tar_record.should_stop:
                        tar_record.last_message = "❌ Processing stopped by user."
                        tar_record.save()
                        return False, "Processing stopped."
                    if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                        continue

                    full_path = os.path.join(root, file)
                    note_parts = []

                    # Parse filename timestamp
                    filename_timestamp = parse_filename_timestamp_with_fallback(file, note_parts)

                    # OCR timestamp
                    watermark_timestamp = extract_timestamp_from_watermark(full_path)
                    if not watermark_timestamp:
                        note_parts.append("Watermark timestamp missing")
                        watermark_timestamp = DUMMY_DATE

                    # Destination path
                    dest_rel_path = os.path.join(
                        "all_sky_images",
                        filename_timestamp.strftime("%Y"),
                        filename_timestamp.strftime("%m"),
                        filename_timestamp.strftime("%d"),
                        file,
                    )
                    dest_full_path = os.path.join(Path().resolve(), "media", dest_rel_path)
                    os.makedirs(os.path.dirname(dest_full_path), exist_ok=True)
                    shutil.copy2(full_path, dest_full_path)

                    preview = generate_thumbnail_bytes(full_path)
                    final_timestamp = watermark_timestamp if watermark_timestamp != DUMMY_DATE else filename_timestamp

                    AllSkyImage.objects.create(
                        file=dest_rel_path.replace("\\", "/"),
                        final_timestamp=final_timestamp,
                        filename_timestamp=filename_timestamp,
                        watermark_timestamp=watermark_timestamp,
                        timestamp_mismatch=(filename_timestamp != watermark_timestamp),
                        preview=preview,
                        note=" | ".join(note_parts),
                    )

                    count += 1
                    if count % 10 == 0:
                        tar_record.last_message = f"Processed {count} images..."
                        tar_record.save()
            tar_record.is_processing = False
            tar_record.last_message = f"✅ Finished. {count} images processed."
            tar_record.save()
            return True, f"{count} images processed."
    
        except Exception as e:
            tar_record.is_processing = False
            tar_record.last_message = f"❌ Error: {e}"
            tar_record.save()
            return False, str(e)


def parse_filename_timestamp_with_fallback(filename, note_parts):
    try:
        parts = filename.split("_")
        date_part = parts[2]
        time_part = parts[3].replace("-", ":").split(".")[0]
        h, m, s = time_part.strip().split(":")[:3]
        timestamp_str = f"{date_part} {h.zfill(2)}:{m.zfill(2)}:{s.zfill(2)}"
        return datetime.strptime(timestamp_str, "%y-%m-%d %H:%M:%S")
    except Exception as e:
        note_parts.append(f"Filename timestamp parsing failed: {e}")
        return DUMMY_DATE
    
def handle_directory_ingestion(directory, station, media_root):
    count = 0
    errors = []
    for root, _, files in os.walk(directory):
        for file in files:
            try:
                full_path = os.path.join(root, file)
                is_image = file.lower().endswith(('.jpg', '.jpeg', '.png'))
                is_video = file.lower().endswith('.avi')
                if not (is_image or is_video):
                    continue

                filename_timestamp = parse_filename_timestamp(file)
                if not filename_timestamp:
                    raise ValueError("Invalid filename timestamp")

                watermark_timestamp = extract_timestamp_from_watermark(full_path) if is_image else None
                preview_bytes = generate_thumbnail_bytes(full_path) if is_image else None
                timestamp_mismatch = (filename_timestamp != watermark_timestamp) if watermark_timestamp else False
                final_timestamp = watermark_timestamp or filename_timestamp

                sub_folder = "avi" if is_video else ""
                dest_rel_path = os.path.join(
                    "all_sky_images",
                    station,
                    filename_timestamp.strftime("%Y"),
                    filename_timestamp.strftime("%m"),
                    filename_timestamp.strftime("%d"),
                    sub_folder,
                    file
                )
                dest_full_path = os.path.join(media_root, dest_rel_path)
                os.makedirs(os.path.dirname(dest_full_path), exist_ok=True)
                shutil.copy2(full_path, dest_full_path)

                AllSkyImage.objects.create(
                    file=dest_rel_path.replace("\\", "/"),
                    station=station,
                    filename_timestamp=filename_timestamp,
                    watermark_timestamp=watermark_timestamp or datetime(1970,1,1),
                    timestamp_mismatch=timestamp_mismatch,
                    note="",
                    preview=preview_bytes,
                    final_timestamp=final_timestamp,
                )
                count += 1
            except Exception as e:
                errors.append(f"{file}: {e}")
    return count, errors