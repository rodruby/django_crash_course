from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

# Using Django's built-in JSONField (cross-db; from django.db.models)
from django.db.models import JSONField as DjangoJSONField

class Sale(models.Model):
    """Persistent model representing a single sale row (optional)."""
    upload = models.ForeignKey("Upload", on_delete=models.CASCADE, related_name="sales", null=True, blank=True)
    MLSNumber = models.CharField(max_length=100, blank=True, null=True)
    StreetNumberNumeric = models.IntegerField(blank=True, null=True)
    StreetName = models.CharField(max_length=255, blank=True, null=True)
    City = models.CharField(max_length=120, blank=True, null=True)
    CDOM = models.IntegerField(blank=True, null=True)
    ListPrice = models.FloatField(blank=True, null=True)
    CurrentPrice = models.FloatField(blank=True, null=True)
    ClosePrice = models.FloatField(blank=True, null=True)
    PendingDate = models.DateField(blank=True, null=True)
    CloseDate = models.DateField(blank=True, null=True)
    SqFtTotal = models.FloatField(blank=True, null=True)
    SqFtLivArea = models.FloatField(blank=True, null=True)
    View = models.CharField(max_length=120, blank=True, null=True)
    WaterView = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        mls = self.MLSNumber or "Sale"
        date = self.CloseDate.isoformat() if self.CloseDate else "NoDate"
        return f"{mls} - {date}"

    @property
    def price_per_sf(self) -> float | None:
        """ClosePrice / SqFtLivArea if available else ClosePrice / SqFtTotal."""
        price = self.ClosePrice
        if price is None:
            return None
        sqft = None
        if self.SqFtLivArea and self.SqFtLivArea > 0:
            sqft = self.SqFtLivArea
        elif self.SqFtTotal and self.SqFtTotal > 0:
            sqft = self.SqFtTotal
        if sqft and sqft > 0:
            return price / sqft
        return None


class Upload(models.Model):
    """Store metadata about uploads and results (summary JSON)."""
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey('auth.User', blank=True, null=True, on_delete=models.SET_NULL)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to='uploads/', blank=True, null=True)
    save_sales_to_db = models.BooleanField(default=False)
    rows_processed = models.IntegerField(default=0)
    rows_excluded = models.IntegerField(default=0)
    results_summary = DjangoJSONField(blank=True, null=True)  # store final dict summary

    # NEW: property address for this upload/analysis
    address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        addr = self.address or "NoAddress"
        return f"Upload {self.original_filename} for {addr} @ {self.uploaded_at.isoformat()}"

    class Meta:
        ordering = ['-uploaded_at']

    def get_monthly_data(self):
        """Extract monthly table data from results_summary."""
        if not self.results_summary:
            return []
        return self.results_summary.get('monthly_table', [])

    def get_yearly_data(self):
        """Extract yearly table data from results_summary."""
        if not self.results_summary:
            return []
        return self.results_summary.get('yearly_table', [])


class TimeAdjustmentAnalysis(models.Model):
    """
    Stores time adjustment analysis for a specific effective date and set of comparable sales.
    """
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="time_adjustments")
    effective_date = models.DateField(help_text="The appraisal effective date")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Store analysis results as JSON
    results = DjangoJSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Time Adjustment Analysis"
        verbose_name_plural = "Time Adjustment Analyses"

    def __str__(self):
        return f"Time Adjustment for {self.upload.address} - {self.effective_date}"


class ComparableSale(models.Model):
    """
    Represents a comparable sale for time adjustment calculation.
    """
    analysis = models.ForeignKey(
        TimeAdjustmentAnalysis,
        on_delete=models.CASCADE,
        related_name="comparable_sales"
    )
    sale_date = models.DateField(help_text="The sale date of the comparable")
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Sale price of the comparable property"
    )
    square_footage = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Living area square footage (optional)"
    )
    address = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Property address (optional)"
    )

    # Time adjustment results (calculated)
    monthly_price_adjustment = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Monthly median price adjustment (%)"
    )
    monthly_psf_adjustment = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Monthly median PSF adjustment (%)"
    )
    linear_price_adjustment = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Linear trendline price adjustment (%)"
    )
    linear_psf_adjustment = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Linear trendline PSF adjustment (%)"
    )
    polynomial_price_adjustment = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Polynomial trendline price adjustment (%)"
    )
    polynomial_psf_adjustment = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Polynomial trendline PSF adjustment (%)"
    )

    class Meta:
        ordering = ['sale_date']

    def __str__(self):
        addr = self.address or f"Sale ${self.sale_price:,.0f}"
        return f"{addr} - {self.sale_date}"

    @property
    def price_per_sf(self):
        """Calculate price per square foot if square footage is available."""
        if self.square_footage and self.square_footage > 0:
            return self.sale_price / self.square_footage
        return None
