from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from .models import TarFileRecord, AllSkyImage
from .views import admin_process_tar_file
from .management.commands.scan_tar_files import Command as ScanCommand
from .utils import handle_directory_ingestion
from django.template.response import TemplateResponse
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
import zipfile
import os
@admin.register(TarFileRecord)
class TarFileRecordAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'processed', 'last_processed', 'process_button','processing_controls','status_label')
    list_filter = ('processed',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ingest-tar/<int:tar_id>/', self.admin_site.admin_view(admin_process_tar_file), name='process_tar_admin'),
            path('scan-tar-files/', self.admin_site.admin_view(self.scan_tar_files), name='scan_tar_files'),
        ]
        return custom_urls + urls

    def scan_tar_files(self, request):
        ScanCommand().handle()
        self.message_user(request, "Tar file list refreshed.")
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['scan_tar_url'] = reverse('admin:scan_tar_files')
        return super().changelist_view(request, extra_context=extra_context)
    
    def process_button(self, obj):
        if obj.processed:
            label = "Reprocess"
        else:
            label = "Process"

        return format_html(
            '<button type="button" class="button ajax-process-btn" data-tar-id="{}">{}</button>',
            obj.id,
            label
        )
    def processing_controls(self, obj):
        return format_html('''
            <div id="status-{id}">Status: ⏸ Not running</div>
            <button onclick="startIngestion({id})">▶ Start</button>
            <button onclick="stopIngestion({id})">🛑 Stop</button>
        ''', id=obj.id)
    processing_controls.short_description = "Ingest Controls"

    @admin.display(description="Status")
    def status_label(self, obj):
        if obj.is_processing:
            return "🟡 Processing"
        elif obj.processed:
            return "✅ Done"
        else:
            return "⏸ Not Started"

class DirectoryIngestionForm(forms.Form):
    station = forms.CharField(max_length=100, required=True)
    directory = forms.CharField(widget=forms.TextInput(attrs={'size': 100}), required=True)

@admin.register(AllSkyImage)
class AllSkyImageAdmin(admin.ModelAdmin):
    change_list_template = "admin/gallery/allskyimage/change_list.html"
    fields = ('file', 'station', 'note', 'filename_timestamp', 'watermark_timestamp', 'final_timestamp', 'timestamp_mismatch')
    readonly_fields = ('filename_timestamp', 'watermark_timestamp', 'final_timestamp', 'timestamp_mismatch')
    list_display = ('file', 'formatted_final_timestamp', 'timestamp_mismatch')
    list_filter = ('timestamp_mismatch', 'final_timestamp')
    search_fields = ('file',)

    def formatted_final_timestamp(self, obj):
        return obj.final_timestamp.strftime("%Y-%m-%d %H:%M:%S") if obj.final_timestamp else "-"
    formatted_final_timestamp.short_description = "Final Timestamp"
    formatted_final_timestamp.admin_order_field = 'final_timestamp'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), name='bulk_upload_allskyimage'),
            path('ingest-directory/', self.admin_site.admin_view(self.ingest_directory_view), name='ingest_directory'),
        ]
        return custom + urls

    def ingest_directory_view(self, request):
        form = DirectoryIngestionForm(request.POST or None)

        if request.method == "POST" and form.is_valid():
            station = form.cleaned_data['station']
            directory = form.cleaned_data['directory']
            count, errors = handle_directory_ingestion(directory, station, settings.MEDIA_ROOT)
            self.message_user(request, f"{count} files ingested. {len(errors)} errors.")
            return redirect("..")

        context = dict(
            self.admin_site.each_context(request),
            title="Ingest AllSky Dataset from Directory",
            form=form,
        )
        return TemplateResponse(request, "admin/ingest_directory.html", context)

    def bulk_upload_view(self, request):
        from .forms import BulkUploadForm
        form = BulkUploadForm(request.POST or None, request.FILES or None)

        if request.method == "POST" and form.is_valid():
            station = form.cleaned_data['station']
            zip_file = form.cleaned_data['zip_file']

            import zipfile
            from django.core.files.base import ContentFile
            count = 0

            with zipfile.ZipFile(zip_file) as zf:
                for file_name in zf.namelist():
                    if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.avi', '.mp4')):
                        data = zf.read(file_name)
                        content = ContentFile(data, name=os.path.basename(file_name))
                        AllSkyImage.objects.create(file=content, station=station)
                        count += 1

            self.message_user(request, f"{count} files uploaded successfully.")
            return redirect("..")

        context = dict(
            self.admin_site.each_context(request),
            title="Bulk Upload AllSky Files",
            form=form,
        )
        return TemplateResponse(request, "admin/bulk_upload.html", context)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return ()

    def get_fields(self, request, obj=None):
        if obj:
            return ('file', 'station', 'note') + self.readonly_fields
        return ('file', 'station', 'note')