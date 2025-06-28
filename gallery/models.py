from django.db import models

class AllSkyImage(models.Model):
    file = models.ImageField(upload_to='all_sky_images/%Y-%m-%d/')
    
    filename_timestamp = models.DateTimeField()
    watermark_timestamp = models.DateTimeField()
    timestamp_mismatch = models.BooleanField(default=False)
    note = models.TextField(blank=True, null=True)
    preview = models.BinaryField(blank=True, null=True)
    final_timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} ({self.filename_timestamp})"
    

class TarFileRecord(models.Model):
    file_path = models.CharField(max_length=500, unique=True)
    file_name = models.CharField(max_length=255)
    processed = models.BooleanField(default=False)
    last_processed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.file_name