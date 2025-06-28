from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from .models import TarFileRecord, AllSkyImage
from .views import admin_process_tar_file
from .management.commands.scan_tar_files import Command as ScanCommand


@admin.register(TarFileRecord)
class TarFileRecordAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'processed', 'last_processed', 'process_button')
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
        url = reverse('admin:process_tar_admin', args=[obj.id])
        label = "Reprocess" if obj.processed else "Process"
        return format_html('<a class="button" href="{}">{}</a>', url, label)
    process_button.short_description = "Action"

@admin.register(AllSkyImage)
class AllSkyImageAdmin(admin.ModelAdmin):
    list_display = ('file', 'final_timestamp', 'timestamp_mismatch')
    list_filter = ('timestamp_mismatch', 'final_timestamp')
    search_fields = ('file',)