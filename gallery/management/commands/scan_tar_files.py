import os
from django.core.management.base import BaseCommand
from gallery.models import TarFileRecord

class Command(BaseCommand):
    help = "Scans raw_data/all_sky_dataset for new .tar files"

    def handle(self, *args, **kwargs):
        base_dir = 'raw_data/all_sky_dataset'
        new_files = 0

        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.tar'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, base_dir)

                    if not TarFileRecord.objects.filter(file_path=rel_path).exists():
                        TarFileRecord.objects.create(
                            file_path=rel_path,
                            file_name=file,
                            processed=False
                        )
                        new_files += 1

        self.stdout.write(self.style.SUCCESS(f"{new_files} new .tar files registered."))
