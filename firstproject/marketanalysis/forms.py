# forms.py
from django import forms
from django.forms import formset_factory
from .models import Upload, TimeAdjustmentAnalysis, ComparableSale
from decimal import Decimal
import datetime

class CSVUploadForm(forms.ModelForm):
    """Form for uploading MLS CSV/Excel files."""

    class Meta:
        model = Upload
        fields = ['address', 'file', 'save_sales_to_db']
        labels = {
            'address': 'Property Address',
            'file': 'CSV or Excel file (.csv, .xls, .xlsx)',
            'save_sales_to_db': 'Save individual sales to database',
        }
        help_texts = {
            'file': 'Upload a CSV or Excel file exported from MLS with ClosePrice, CloseDate, and square footage data.',
            'address': 'Property address for this analysis (optional but recommended)',
            'save_sales_to_db': 'Check this to store individual sale records (useful for large datasets)',
        }
        widgets = {
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123 Main St, City, State'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.csv,.xls,.xlsx'
            }),
            'save_sales_to_db': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_file(self):
        f = self.cleaned_data['file']
        name = f.name.lower()
        allowed = ('.csv', '.xls', '.xlsx')
        if not any(name.endswith(ext) for ext in allowed):
            raise forms.ValidationError("Unsupported file type. Upload .csv, .xls, or .xlsx")
        max_mb = 10
        if f.size > max_mb * 1024 * 1024:
            raise forms.ValidationError(f"File too large. Max {max_mb} MB.")
        return f


class TimeAdjustmentForm(forms.ModelForm):
    """Form for creating a time adjustment analysis."""

    class Meta:
        model = TimeAdjustmentAnalysis
        fields = ['effective_date']
        labels = {
            'effective_date': 'Effective Appraisal Date',
        }
        help_texts = {
            'effective_date': 'The date for which you need the market value (typically the appraisal date)',
        }
        widgets = {
            'effective_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': datetime.date.today().isoformat()
            })
        }

    def clean_effective_date(self):
        date = self.cleaned_data['effective_date']
        if date > datetime.date.today():
            raise forms.ValidationError("Effective date cannot be in the future.")
        return date


class ComparableSaleForm(forms.ModelForm):
    """Form for individual comparable sales in the formset."""

    class Meta:
        model = ComparableSale
        fields = ['sale_date', 'sale_price', 'square_footage', 'address']
        labels = {
            'sale_date': 'Sale Date',
            'sale_price': 'Sale Price ($)',
            'square_footage': 'Living Area (sq ft)',
            'address': 'Property Address',
        }
        widgets = {
            'sale_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': datetime.date.today().isoformat()
            }),
            'sale_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': '500000'
            }),
            'square_footage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': '2000'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '456 Oak Ave, City, State'
            })
        }

    def clean_sale_date(self):
        date = self.cleaned_data['sale_date']
        if date > datetime.date.today():
            raise forms.ValidationError("Sale date cannot be in the future.")
        return date

    def clean_sale_price(self):
        price = self.cleaned_data['sale_price']
        if price <= 0:
            raise forms.ValidationError("Sale price must be greater than zero.")
        return price


# Create formset for multiple comparable sales
ComparableSaleFormSet = formset_factory(
    ComparableSaleForm,
    extra=3,  # Start with 3 empty forms
    max_num=20,  # Maximum 20 comparables
    can_delete=True,
    validate_max=True
)
