from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from .models import TarFileRecord, AllSkyImage
from .views import admin_process_tar_file
from .management.commands.scan_tar_files import Command as ScanCommand

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

@admin.register(AllSkyImage)
class AllSkyImageAdmin(admin.ModelAdmin):
    list_display = ('file', 'formatted_final_timestamp', 'timestamp_mismatch')
    list_filter = ('timestamp_mismatch', 'final_timestamp')
    search_fields = ('file',)

    def formatted_final_timestamp(self, obj):
        return obj.final_timestamp.strftime("%Y-%m-%d %H:%M:%S") if obj.final_timestamp else "-"
    formatted_final_timestamp.short_description = "Final Timestamp"
    formatted_final_timestamp.admin_order_field = 'final_timestamp'