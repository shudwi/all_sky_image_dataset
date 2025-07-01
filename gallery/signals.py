from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AllSkyImage
from .utils import (
    generate_thumbnail_bytes,
    generate_video_thumbnail_bytes,
    extract_timestamp_from_watermark,
    parse_filename_timestamp,
)
from datetime import datetime
import os
import ffmpeg
from pathlib import Path

DUMMY_DATE = datetime(1900, 1, 1)

def is_dummy(date):
    return date is None or date == DUMMY_DATE

@receiver(post_save, sender=AllSkyImage)
def process_allskyimage(sender, instance, created, **kwargs):
    updates = {}
    print("Post-save signal triggered")

    # ----- Convert .avi to .mp4 after file is saved -----
    if instance.file and instance.is_video():
        input_path = Path(instance.file.path)
        if input_path.suffix.lower() == ".avia":
            output_path = input_path.with_suffix(".mp4")
            if not output_path.exists():
                try:
                    ffmpeg.input(str(input_path)).output(
                        str(output_path),
                        vcodec="libx264",
                        acodec="aac"
                    ).run(overwrite_output=True)

                    # Remove the .avi file
                    os.remove(str(input_path))

                    # Update the instance to point to new .mp4 file
                    instance.file.name = os.path.join(
                        os.path.dirname(instance.file.name),
                        output_path.name
                    )
                    updates['file'] = instance.file.name
                    print(f"Converted AVI to MP4: {output_path.name}")

                except ffmpeg.Error as e:
                    print("FFmpeg conversion error:", e.stderr or str(e))

    # ----- Metadata Parsing -----
    if is_dummy(instance.filename_timestamp):
        filename_ts = parse_filename_timestamp(instance.file.name)
        updates['filename_timestamp'] = filename_ts or DUMMY_DATE

    if is_dummy(instance.watermark_timestamp) and instance.is_image():
        wm_ts = extract_timestamp_from_watermark(instance.file.path)
        updates['watermark_timestamp'] = wm_ts or DUMMY_DATE

    wm_ts = updates.get('watermark_timestamp', instance.watermark_timestamp)
    fn_ts = updates.get('filename_timestamp', instance.filename_timestamp)

    if is_dummy(instance.final_timestamp):
        updates['final_timestamp'] = wm_ts if not is_dummy(wm_ts) else fn_ts

    if not is_dummy(fn_ts) and not is_dummy(wm_ts):
        mismatch = abs((fn_ts - wm_ts).total_seconds()) > 1
        if instance.timestamp_mismatch != mismatch:
            updates['timestamp_mismatch'] = mismatch

    # ----- Generate Preview -----
    if not instance.preview and instance.file:
        if instance.is_image():
            updates['preview'] = generate_thumbnail_bytes(instance.file.path)
        elif instance.is_video():
            updates['preview'] = generate_video_thumbnail_bytes(instance.file.path)

    if updates:
        AllSkyImage.objects.filter(pk=instance.pk).update(**updates)
        print("Fields updated:", list(updates.keys()))