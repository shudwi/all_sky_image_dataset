from django.shortcuts import render
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.http import HttpResponse, Http404
from .models import TarFileRecord, AllSkyImage
from .utils import process_tar_file, admin_process_tar_archive
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from datetime import date
import os
import threading
from django.http import JsonResponse
import calendar
from django.db.models.functions import TruncDay
from django.db.models import Count

DUMMY_DATE = datetime(1900, 1, 1, 0, 0, 0)

def home(request):
    years = AllSkyImage.objects.dates('final_timestamp', 'year')
    return render(request, 'gallery/home.html', {'years': years})

def year_view(request, year):
    months = AllSkyImage.objects.filter(final_timestamp__year=year).dates('final_timestamp', 'month')
    month_names = list(calendar.month_name)[1:]  # Skips empty string at index 0
    return render(request, 'gallery/year.html', {
        'year': year,
        'months': months,
        'month_names': month_names,
    })

def month_view(request, year, month):

    # Get all days with data
    all_days = AllSkyImage.objects.filter(
        final_timestamp__year=year
    ).dates('final_timestamp', 'day')
    days_with_data = set(all_days)

    # Build calendar for all 12 months
    cal = calendar.Calendar(firstweekday=6)
    months = []
    for m in range(1, 13):
        month_data = {
            'name': calendar.month_name[m],
            'number': m,
            'weeks': []
        }
        for week in cal.monthdatescalendar(year, m):
            week_data = []
            for day in week:
                if day.month != m:
                    week_data.append({'day': '', 'status': 'empty'})
                else:
                    status = 'available' if day in days_with_data else 'unavailable'
                    week_data.append({'day': day.day, 'date': day, 'status': status})
            month_data['weeks'].append(week_data)
        months.append(month_data)

    return render(request, 'gallery/month.html', {
        'year': year,
        'months': months,
    })

def day_gallery(request, year, month, day):

    date_selected = date(year, month, day)
    start_dt = datetime.combine(date_selected, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    images = AllSkyImage.objects.filter(filename_timestamp__gte=start_dt,
    filename_timestamp__lt=end_dt).order_by('final_timestamp')
    first_image = images.first()

    paginator = Paginator(images, 50)
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
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            images = AllSkyImage.objects.filter(final_timestamp__date=date_obj).order_by('-filename_timestamp')
        except ValueError:
            pass
    else:
        images = AllSkyImage.objects.all().order_by('-filename_timestamp')
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
    rerun = request.GET.get("rerun") == "1"
    tar_record = TarFileRecord.objects.get(id=tar_id)

    if not rerun and tar_record.processed:
        return HttpResponse("Already processed.")

    full_tar_path = os.path.join('raw_data/all_sky_dataset', tar_record.file_path)
    process_tar_file(full_tar_path, tar_record, settings.MEDIA_ROOT)

    tar_record.processed = True
    tar_record.last_processed = now()
    tar_record.save()

    return HttpResponse("Done processing.")


def admin_process_tar_file(request, tar_id):
    tar_record = get_object_or_404(TarFileRecord, id=tar_id)
    success, message = admin_process_tar_archive(tar_record)

    if success:
        tar_record.processed = True
        tar_record.last_processed = now()
        tar_record.save()
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("..")

def async_ingest_tar(request, tar_id):
    def background_task():
        print("#### 2")
        tar_record = TarFileRecord.objects.get(id=tar_id)
        print("#### 3")
        success, msg = admin_process_tar_archive(tar_record)
        if success:
            tar_record.processed = True
            tar_record.last_processed = now()
            tar_record.save()
    print("#### 1")
    threading.Thread(target=background_task).start()

    return JsonResponse({"status": "started", "message": f"Ingestion started for TAR ID {tar_id}"})

def get_tar_status(request, tar_id):
    tar_record = get_object_or_404(TarFileRecord, id=tar_id)
    return JsonResponse({
        'is_processing': tar_record.is_processing,
        'last_message': tar_record.last_message,
        'can_stop': tar_record.is_processing,
    })

def stop_tar_process(request, tar_id):
    tar_record = get_object_or_404(TarFileRecord, id=tar_id)
    if tar_record.is_processing:
        tar_record.should_stop = True
        tar_record.last_message = "🛑 Stop requested..."
        tar_record.save()
        return JsonResponse({"status": "stop_requested"})
    return JsonResponse({"status": "not_processing"})

def async_status_view(request, tar_id):
    try:
        tar = TarFileRecord.objects.get(id=tar_id)
        return JsonResponse({
            "is_processing": tar.is_processing,
            "last_message": tar.last_message or "⏸ Not running"
        })
    except TarFileRecord.DoesNotExist:
        return JsonResponse({"is_processing": False, "last_message": "❌ Not found"})

def stop_ingest_view(request, tar_id):
    try:
        tar = TarFileRecord.objects.get(id=tar_id)
        tar.should_stop = True
        tar.last_message = "🛑 Stop requested..."
        tar.is_processing = False
        tar.save()
        return JsonResponse({"message": "Stop signal sent."})
    except TarFileRecord.DoesNotExist:
        return JsonResponse({"message": "Not found."}, status=404)
    
def ingest_thread_model(tar):
    tar.is_processing = True
    tar.last_message = "🚀 Starting ingestion..."
    tar.should_stop = False
    tar.save()

    success, message = admin_process_tar_archive(tar)

    tar.is_processing = False
    tar.last_message = f"✅ Done: {message}" if success else f"❌ Failed: {message}"
    tar.save()

def async_ingest_view(request, tar_id):
    try:
        tar = TarFileRecord.objects.get(id=tar_id)
        if tar.is_processing:
            return JsonResponse({"message": "Already processing."})

        thread = threading.Thread(target=ingest_thread_model, args=(tar,))
        thread.start()

        return JsonResponse({"message": "Started processing."})
    except TarFileRecord.DoesNotExist:
        return JsonResponse({"message": "Not found."}, status=404)