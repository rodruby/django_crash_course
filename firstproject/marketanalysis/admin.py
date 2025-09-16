from django.contrib import admin

# Register your models here.
from .models import Sale, Upload

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("MLSNumber", "CloseDate", "ClosePrice", "City")
    search_fields = ("MLSNumber", "StreetName", "City")

@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "uploaded_at", "rows_processed", "rows_excluded", "save_sales_to_db")
    readonly_fields = ("results_summary",)