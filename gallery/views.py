from django.shortcuts import render
import shutil
from django.utils.timezone import now
import tarfile, os, shutil
from datetime import datetime, timedelta
from django.http import HttpResponse, Http404
from .models import TarFileRecord, AllSkyImage
from .utils import extract_timestamp_from_watermark, generate_thumbnail_bytes
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.utils.timezone import now
from django.core.paginator import Paginator
from datetime import date
from django.db.models.functions import TruncDate
from django.db.models import Count

DUMMY_DATE = datetime(1900, 1, 1, 0, 0, 0)

def home(request):
    years = AllSkyImage.objects.dates('final_timestamp', 'year')
    return render(request, 'gallery/home.html', {'years': years})

def year_view(request, year):
    months = AllSkyImage.objects.filter(final_timestamp__year=year) \
        .dates('final_timestamp', 'month')
    return render(request, 'gallery/year.html', {'year': year, 'months': months})

def month_view(request, year, month):
    days = AllSkyImage.objects.filter(final_timestamp__year=year, final_timestamp__month=month) \
        .dates('final_timestamp', 'day')
    return render(request, 'gallery/month.html', {'year': year, 'month': month, 'days': days})

def day_gallery(request, year, month, day):

    date_selected = date(year, month, day)
    start_dt = datetime.combine(date_selected, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    images = AllSkyImage.objects.filter(filename_timestamp__gte=start_dt,
    filename_timestamp__lt=end_dt).order_by('final_timestamp')
    first_image = images.first()

    paginator = Paginator(images, 30)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'gallery/day_gallery.html', {
        'date': date_selected,
        'first_image': first_image,
        'page_obj': page_obj,
    })

def gallery_by_date(request, date=None):
    images = AllSkyImage.objects.none()
    date_obj = None
    print("#### 1")
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            images = AllSkyImage.objects.filter(final_timestamp__date=date_obj).order_by('-filename_timestamp')
            print("#### 2")
        except ValueError:
            print("#### 3")
            pass
    else:
        images = AllSkyImage.objects.all().order_by('-filename_timestamp')
        print("#### 4")
    # Pagination setup — 100 images per page
    paginator = Paginator(images, 100)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'gallery/gallery.html', {
        'page_obj': page_obj,
        'date': date,
        'date_obj': date_obj,
    })

def preview_image_view(request, image_id):
    try:
        img = AllSkyImage.objects.get(id=image_id)
        if img.preview:
            return HttpResponse(img.preview, content_type="image/jpeg")
        else:
            raise Http404("Preview not available")
    except AllSkyImage.DoesNotExist:
        raise Http404("Image not found")

def process_tar_view(request, tar_id):
    from config import settings  # or use settings.MEDIA_ROOT

    rerun = request.GET.get("rerun") == "1"
    tar_record = TarFileRecord.objects.get(id=tar_id)
    full_tar_path = os.path.join('raw_data/all_sky_dataset', tar_record.file_path)

    if not rerun and tar_record.processed:
        return HttpResponse("Already processed.")

    temp_extract_path = "/tmp/extracted_images"
    if os.path.exists(temp_extract_path):
        shutil.rmtree(temp_extract_path)
    os.makedirs(temp_extract_path, exist_ok=True)

    with tarfile.open(full_tar_path) as tar:
        tar.extractall(temp_extract_path)

    for root, _, files in os.walk(temp_extract_path):
        for file in files:
            if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            full_path = os.path.join(root, file)

            # Parse filename timestamp
            try:
                parts = file.split("_")
                date_part = parts[2]  # e.g. 20-03-01
                time_part = parts[3].replace("-", ":").replace(".jpg", "")
                filename_timestamp = datetime.strptime(f"{date_part} {time_part}", "%y-%m-%d %H:%M:%S")
            except:
                continue

            # OCR watermark
            watermark_timestamp = extract_timestamp_from_watermark(full_path)

            # Prepare destination
            dest_rel_path = f"all_sky_images/{filename_timestamp.strftime('%Y/%m/%d')}/{file}"
            dest_full_path = os.path.join(settings.MEDIA_ROOT, dest_rel_path)
            os.makedirs(os.path.dirname(dest_full_path), exist_ok=True)
            shutil.copy2(full_path, dest_full_path)

            preview_bytes = generate_thumbnail_bytes(full_path)

            AllSkyImage.objects.create(
                file=dest_rel_path,
                filename_timestamp=filename_timestamp,
                watermark_timestamp=watermark_timestamp,
                timestamp_mismatch=(filename_timestamp != watermark_timestamp),
                preview=preview_bytes,
            )

    tar_record.processed = True
    tar_record.last_processed = now()
    tar_record.save()
    return HttpResponse("Done processing.")

def admin_process_tar_file(request, tar_id):
    tar_record = get_object_or_404(TarFileRecord, id=tar_id)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_extract_path = f"/tmp/sky_gallery_extract_{tar_id}_{timestamp_str}"
    full_tar_path = os.path.join("raw_data/all_sky_dataset", tar_record.file_path)

    if not os.path.exists(full_tar_path):
        messages.error(request, "TAR file not found.")
        return redirect("..")

    # Reset if reprocessing
    if os.path.exists(temp_extract_path):
        shutil.rmtree(temp_extract_path)
    os.makedirs(temp_extract_path, exist_ok=True)

    with tarfile.open(full_tar_path) as tar:
        tar.extractall(temp_extract_path)

    count = 0
    for root, _, files in os.walk(temp_extract_path):
        for file in files:
            if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            full_path = os.path.join(root, file)
            note_parts = []
            try:
                parts = file.split("_")
                date_part = parts[2]
                time_part = parts[3].replace("-", ":").replace(".jpg", "")
                time_clean = time_part.strip().split(':')[:3]  # keep only HH:MM:SS
                timestamp_str = f"{date_part} {'{:0>2}:{:0>2}:{:0>2}'.format(*time_clean)}"
                filename_timestamp = datetime.strptime(timestamp_str, "%y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"❌ Error parsing datetime from filename: {file} — {e}")
                filename_timestamp = DUMMY_DATE
                note_parts.append(f"Filename timestamp parsing failed: {e}")
            watermark_timestamp = extract_timestamp_from_watermark(full_path)
            if not watermark_timestamp:
                print(f"❌ Watermark timestamp not found for: {file}")
                watermark_timestamp = DUMMY_DATE
                note_parts.append("Watermark timestamp missing")
            dest_rel_path = f"all_sky_images/{filename_timestamp.strftime('%Y/%m/%d')}/{file}"
            dest_full_path = os.path.join(settings.MEDIA_ROOT, dest_rel_path)
            os.makedirs(os.path.dirname(dest_full_path), exist_ok=True)
            shutil.copy2(full_path, dest_full_path)

            preview = generate_thumbnail_bytes(full_path)
            final_timestamp = watermark_timestamp if watermark_timestamp != DUMMY_DATE else filename_timestamp
            AllSkyImage.objects.create(
                file=dest_rel_path,
                final_timestamp=final_timestamp,
                filename_timestamp=filename_timestamp,
                watermark_timestamp=watermark_timestamp,
                timestamp_mismatch=(filename_timestamp != watermark_timestamp),
                preview=preview,
                note=" | ".join(note_parts),
            )
            count += 1

    tar_record.processed = True
    tar_record.last_processed = now()
    tar_record.save()

    messages.success(request, f"{count} images processed.")
    return redirect("..")

