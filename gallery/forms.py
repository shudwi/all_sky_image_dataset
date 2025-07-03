from django import forms
from .models import AllSkyImage

class BulkUploadForm(forms.Form):
    station = forms.ChoiceField(
        choices=AllSkyImage.StationChoices.choices,
        initial=AllSkyImage.StationChoices.BHARATI,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    zip_file = forms.FileField(
        help_text="Upload a ZIP file containing images or videos",
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        required=True
    )


class DirectoryIngestionForm(forms.Form):
    station = forms.ChoiceField(
        choices=AllSkyImage.StationChoices.choices,
        initial=AllSkyImage.StationChoices.BHARATI,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    directory = forms.CharField(
        widget=forms.TextInput(attrs={'size': 100, 'class': 'form-control'}),
        required=True
    )