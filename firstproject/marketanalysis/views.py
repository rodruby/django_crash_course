from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, FormView
from django.views.generic.detail import SingleObjectMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .forms import CSVUploadForm, TimeAdjustmentForm, ComparableSaleFormSet
from .models import Upload, Sale, TimeAdjustmentAnalysis, ComparableSale
from .utils.csv_processing import parse_and_clean_file, analyze_sales_dataframe
from .utils.time_adjustments import process_time_adjustments, generate_trendline_data

import json
import pandas as pd
import numpy as np
import datetime
import logging

logger = logging.getLogger(__name__)

class UploadCreateView(CreateView):
    """
    Class-based view for uploading and processing MLS CSV/Excel files.
    """
    model = Upload
    form_class = CSVUploadForm
    template_name = 'marketanalysis/upload.html'
    success_url = reverse_lazy('marketanalysis:analysis_list')

    def form_valid(self, form):
        """Process the uploaded file and save analysis results."""
        try:
            with transaction.atomic():
                # Save the upload instance first
                self.object = form.save(commit=False)
                if self.request.user.is_authenticated:
                    self.object.uploaded_by = self.request.user
                self.object.save()

                uploaded_file = form.cleaned_data['file']
                save_to_db = form.cleaned_data['save_sales_to_db']

                # Process the uploaded file
                df, rows_excluded = parse_and_clean_file(uploaded_file)
                analysis_results = analyze_sales_dataframe(df, n_last_months=12)
                analysis_results['rows_excluded'] = rows_excluded
                analysis_results['rows_processed'] = int(len(df))

                # Optionally save individual sales to database
                if save_to_db:
                    self._save_sales_to_database(df, self.object)

                # Save analysis summary
                self.object.rows_processed = int(len(df))
                self.object.rows_excluded = rows_excluded
                self.object.results_summary = analysis_results
                self.object.save()

                messages.success(
                    self.request,
                    f"Successfully processed {len(df)} records. "
                    f"Analysis saved for {self.object.address or 'upload'}."
                )

                # Redirect to the analysis detail view
                return HttpResponseRedirect(
                    reverse('marketanalysis:view_analysis', kwargs={'pk': self.object.pk})
                )

        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            if hasattr(self, 'object') and self.object:
                self.object.results_summary = {"error": str(e)}
                self.object.save()
            messages.error(self.request, f"Error processing file: {e}")
            return self.form_invalid(form)

    def _save_sales_to_database(self, df: pd.DataFrame, upload: Upload):
        """Save individual sales records to the database."""
        sales_to_create = []
        for _, row in df.iterrows():
            sale = Sale(
                upload=upload,
                MLSNumber=row.get('MLSNumber'),
                StreetName=row.get('StreetName'),
                StreetNumberNumeric=int(row['StreetNumberNumeric']) if 'StreetNumberNumeric' in row and not pd.isna(row['StreetNumberNumeric']) else None,
                City=row.get('City'),
                CDOM=int(row['CDOM']) if 'CDOM' in row and not pd.isna(row['CDOM']) else None,
                ListPrice=float(row['ListPrice']) if 'ListPrice' in row and not pd.isna(row['ListPrice']) else None,
                CurrentPrice=float(row['CurrentPrice']) if 'CurrentPrice' in row and not pd.isna(row['CurrentPrice']) else None,
                ClosePrice=float(row['ClosePrice']) if not pd.isna(row['ClosePrice']) else None,
                PendingDate=row.get('PendingDate') if 'PendingDate' in row else None,
                CloseDate=row.get('CloseDate'),
                SqFtTotal=float(row['SqFtTotal']) if 'SqFtTotal' in row and not pd.isna(row['SqFtTotal']) else None,
                SqFtLivArea=float(row['SqFtLivArea']) if 'SqFtLivArea' in row and not pd.isna(row['SqFtLivArea']) else None,
                View=row.get('View'),
                WaterView=row.get('WaterView'),
            )
            sales_to_create.append(sale)

        Sale.objects.bulk_create(sales_to_create)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Upload MLS Data'
        return context



class AnalysisListView(ListView):
    """
    List view for all uploaded analyses.
    """
    model = Upload
    template_name = 'marketanalysis/analysis_list.html'
    context_object_name = 'uploads'
    paginate_by = 20

    def get_queryset(self):
        return Upload.objects.select_related('uploaded_by').order_by('-uploaded_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Market Analysis Dashboard'
        return context

class AnalysisDetailView(DetailView):
    """
    Detailed view of a market analysis with charts and time adjustment capability.
    """
    model = Upload
    template_name = 'marketanalysis/view_analysis.html'
    context_object_name = 'upload'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        upload = self.object

        # Basic analysis data
        context['results'] = upload.results_summary or {}
        context['sales'] = upload.sales.all()[:100]  # Limit for performance
        context['sales_count'] = upload.sales.count()

        # Monthly and yearly data for charts
        monthly_data = upload.get_monthly_data()
        yearly_data = upload.get_yearly_data()

        context['monthly_data'] = monthly_data
        context['yearly_data'] = yearly_data

        # Generate trendline data for charts
        if monthly_data:
            context['price_trendlines'] = generate_trendline_data(monthly_data, 'median_close')
            context['psf_trendlines'] = generate_trendline_data(monthly_data, 'median_pps')
        else:
            context['price_trendlines'] = {'linear': [], 'polynomial': []}
            context['psf_trendlines'] = {'linear': [], 'polynomial': []}

        # Time adjustment analyses for this upload
        context['time_adjustments'] = upload.time_adjustments.all()

        # Chart data as JSON for JavaScript
        context['chart_data'] = json.dumps({
            'monthly': monthly_data,
            'yearly': yearly_data,
            'price_trendlines': context['price_trendlines'],
            'psf_trendlines': context['psf_trendlines']
        })

        context['page_title'] = f"Analysis: {upload.address or upload.original_filename}"
        return context

class TimeAdjustmentCreateView(SingleObjectMixin, FormView):
    """
    Create a time adjustment analysis with multiple comparable sales.
    """
    model = Upload
    template_name = 'marketanalysis/time_adjustment.html'
    form_class = TimeAdjustmentForm

    def get_object(self):
        return get_object_or_404(Upload, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        # Don't call super() since we're mixing SingleObjectMixin with FormView
        upload = self.get_object()
        context = {'upload': upload}

        if self.request.POST:
            context['formset'] = ComparableSaleFormSet(self.request.POST)
        else:
            context['formset'] = ComparableSaleFormSet()

        # Add form context
        if 'form' not in context:
            context['form'] = self.get_form()

        context['page_title'] = f"Time Adjustment - {upload.address or upload.original_filename}"
        return context

    def form_valid(self, form):
        upload = self.get_object()
        formset = ComparableSaleFormSet(self.request.POST)

        if formset.is_valid():
            try:
                with transaction.atomic():
                    # Create the time adjustment analysis
                    analysis = form.save(commit=False)
                    analysis.upload = upload
                    if self.request.user.is_authenticated:
                        analysis.created_by = self.request.user
                    analysis.save()

                    # Process comparable sales
                    comparable_sales = []
                    for form_data in formset.cleaned_data:
                        if form_data and not form_data.get('DELETE', False):
                            comparable = ComparableSale(
                                analysis=analysis,
                                sale_date=form_data['sale_date'],
                                sale_price=form_data['sale_price'],
                                square_footage=form_data.get('square_footage'),
                                address=form_data.get('address')
                            )
                            comparable_sales.append(comparable)

                    # Save comparable sales
                    ComparableSale.objects.bulk_create(comparable_sales)

                    # Calculate time adjustments
                    adjustment_data = []
                    for comparable in comparable_sales:
                        comp_data = (
                            comparable.sale_date,
                            comparable.sale_price,
                            comparable.square_footage,
                            comparable.address
                        )
                        adjustment_data.append(comp_data)

                    # Process all adjustments
                    adjustment_results = process_time_adjustments(
                        upload.results_summary or {},
                        analysis.effective_date,
                        adjustment_data
                    )

                    # Update comparable sales with calculated adjustments
                    for i, comparable in enumerate(comparable_sales):
                        if i < len(adjustment_results):
                            result = adjustment_results[i]
                            adjustments = result.get('adjustments', {})

                            comparable.monthly_price_adjustment = adjustments.get('monthly_price')
                            comparable.monthly_psf_adjustment = adjustments.get('monthly_psf')
                            comparable.linear_price_adjustment = adjustments.get('linear_price')
                            comparable.linear_psf_adjustment = adjustments.get('linear_psf')
                            comparable.polynomial_price_adjustment = adjustments.get('polynomial_price')
                            comparable.polynomial_psf_adjustment = adjustments.get('polynomial_psf')

                    ComparableSale.objects.bulk_update(
                        comparable_sales,
                        ['monthly_price_adjustment', 'monthly_psf_adjustment',
                         'linear_price_adjustment', 'linear_psf_adjustment',
                         'polynomial_price_adjustment', 'polynomial_psf_adjustment']
                    )

                    # Store complete results in analysis
                    analysis.results = adjustment_results
                    analysis.save()

                    messages.success(
                        self.request,
                        f"Time adjustment analysis completed for {len(comparable_sales)} comparable sales."
                    )

                    return HttpResponseRedirect(
                        reverse('marketanalysis:time_adjustment_detail', kwargs={'pk': analysis.pk})
                    )

            except Exception as e:
                logger.error(f"Error creating time adjustment analysis: {e}")
                messages.error(self.request, f"Error processing time adjustments: {e}")
                return self.form_invalid(form)

        else:
            context = self.get_context_data(form=form)
            context['formset'] = formset
            messages.error(self.request, "Please correct the errors in the comparable sales data.")
            return self.render_to_response(context)


class TimeAdjustmentDetailView(DetailView):
    """
    Display the results of a time adjustment analysis.
    """
    model = TimeAdjustmentAnalysis
    template_name = 'marketanalysis/time_adjustment_detail.html'
    context_object_name = 'analysis'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        analysis = self.object
        context['upload'] = analysis.upload
        context['comparable_sales'] = analysis.comparable_sales.all()
        context['page_title'] = f"Time Adjustment Results - {analysis.effective_date}"
        return context

# Legacy function-based views (kept for backward compatibility)
def hello(request):
    """Simple hello view for the market analysis app."""
    title = "Market Analysis"
    return render(request, 'marketanalysis/index.html', {'title': title})
