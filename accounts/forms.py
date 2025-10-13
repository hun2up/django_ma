# accounts/forms.py
from django import forms

class ExcelUploadForm(forms.Form):
    file = forms.FileField(label='Select an Excel file (.xlsx)')
