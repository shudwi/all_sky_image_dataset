from django import forms

class BulkUploadForm(forms.Form):
    station = forms.CharField(max_length=100)
    zip_file = forms.FileField(help_text="Upload a ZIP file containing images or videos")
