from django.db import models
from datetime import datetime
import os, re

DUMMY_DATE = datetime(1900, 1, 1)

def upload_to_based_on_timestamp(instance, filename):
    dt = instance.final_timestamp
    station = instance.station

    # If final_timestamp is None or dummy, try extracting from filename
    if dt is None or dt == DUMMY_DATE:
        try:
            basename = os.path.basename(filename)  # Just the file name
            # Match pattern like: 2024_09_02__21_46_16.jpg
            match = re.search(r"(\d{4})_(\d{2})_(\d{2})__([0-2]\d)_(\d{2})_(\d{2})", basename)
            if match:
                dt = datetime(
                    int(match.group(1)),  # year
                    int(match.group(2)),  # month
                    int(match.group(3)),  # day
                    int(match.group(4)),  # hour
                    int(match.group(5)),  # minute
                    int(match.group(6))   # second
                )
            else:
                dt = datetime.now()
        except Exception:
            dt = datetime.now()

    return f'all_sky_images/{station}/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/{filename}'
class AllSkyImage(models.Model):
    file = models.FileField(upload_to=upload_to_based_on_timestamp)
    station = models.CharField(max_length=100, default='Bharati')
    filename_timestamp = models.DateTimeField(default=DUMMY_DATE)
    watermark_timestamp = models.DateTimeField(default=DUMMY_DATE)
    timestamp_mismatch = models.BooleanField(default=False)
    note = models.TextField(blank=True, null=True)
    preview = models.BinaryField(blank=True, null=True)
    final_timestamp = models.DateTimeField(default=DUMMY_DATE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} ({self.filename_timestamp})"

    def is_video(self):
        return self.file.name.lower().endswith(('.avi', '.mp4'))

    def is_image(self):
        return self.file.name.lower().endswith(('.jpg', '.jpeg', '.png'))
    

class TarFileRecord(models.Model):
    file_path = models.CharField(max_length=500, unique=True)
    file_name = models.CharField(max_length=255)
    processed = models.BooleanField(default=False)
    last_processed = models.DateTimeField(null=True, blank=True)

    is_processing = models.BooleanField(default=False)
    last_message = models.TextField(blank=True, null=True)
    should_stop = models.BooleanField(default=False)

    def __str__(self):
        return self.file_name