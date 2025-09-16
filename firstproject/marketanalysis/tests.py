"""
Comprehensive unit tests for the marketanalysis Django app.

Tests cover models, views, forms, and utilities including:
- Model validation and methods
- CSV processing and analysis
- Time adjustment calculations
- Form validation
- View functionality
- Template rendering
"""

import os
import json
import tempfile
from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

import pandas as pd
import numpy as np

from .models import Upload, Sale, TimeAdjustmentAnalysis, ComparableSale
from .forms import CSVUploadForm, TimeAdjustmentForm, ComparableSaleFormSet
from .utils.csv_processing import parse_and_clean_file, analyze_sales_dataframe
from .utils.time_adjustments import (
    calculate_monthly_adjustment,
    calculate_linear_trendline_adjustment,
    calculate_polynomial_trendline_adjustment,
    process_time_adjustments,
    generate_trendline_data
)


class ModelTestCase(TestCase):
    """Test cases for Django models."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.upload = Upload.objects.create(
            address='123 Test St, Test City, TS',
            original_filename='test_data.csv',
            uploaded_by=self.user,
            rows_processed=100,
            rows_excluded=5,
            results_summary={
                'monthly_table': [
                    {'year_month': '2023-01', 'median_close': 500000, 'median_pps': 250, 'n': 10},
                    {'year_month': '2023-02', 'median_close': 510000, 'median_pps': 255, 'n': 8}
                ],
                'yearly_table': [
                    {'year': 2023, 'median_close': 505000, 'median_pps': 252.5, 'n': 18}
                ]
            }
        )

    def test_upload_model_str(self):
        """Test Upload model string representation."""
        expected = f"Upload test_data.csv for 123 Test St, Test City, TS @ {self.upload.uploaded_at.isoformat()}"
        self.assertEqual(str(self.upload), expected)

    def test_upload_model_methods(self):
        """Test Upload model helper methods."""
        monthly_data = self.upload.get_monthly_data()
        yearly_data = self.upload.get_yearly_data()

        self.assertEqual(len(monthly_data), 2)
        self.assertEqual(len(yearly_data), 1)
        self.assertEqual(monthly_data[0]['year_month'], '2023-01')
        self.assertEqual(yearly_data[0]['year'], 2023)

    def test_sale_model(self):
        """Test Sale model creation and price_per_sf property."""
        sale = Sale.objects.create(
            upload=self.upload,
            MLSNumber='MLS123456',
            ClosePrice=500000.00,
            CloseDate=date(2023, 1, 15),
            SqFtLivArea=2000.0
        )

        self.assertEqual(sale.price_per_sf, 250.0)
        self.assertIn('MLS123456', str(sale))

    def test_time_adjustment_analysis_model(self):
        """Test TimeAdjustmentAnalysis model."""
        analysis = TimeAdjustmentAnalysis.objects.create(
            upload=self.upload,
            effective_date=date(2023, 6, 1),
            created_by=self.user
        )

        expected_str = f"Time Adjustment for {self.upload.address} - 2023-06-01"
        self.assertEqual(str(analysis), expected_str)

    def test_comparable_sale_model(self):
        """Test ComparableSale model."""
        analysis = TimeAdjustmentAnalysis.objects.create(
            upload=self.upload,
            effective_date=date(2023, 6, 1),
            created_by=self.user
        )

        comparable = ComparableSale.objects.create(
            analysis=analysis,
            sale_date=date(2023, 3, 15),
            sale_price=Decimal('475000.00'),
            square_footage=1900,
            address='456 Comp St'
        )

        self.assertEqual(comparable.price_per_sf, Decimal('250.00'))
        self.assertIn('456 Comp St', str(comparable))


class CSVProcessingTestCase(TestCase):
    """Test cases for CSV processing utilities."""

    def create_test_csv(self, data):
        """Create a test CSV file."""
        csv_content = StringIO()
        df = pd.DataFrame(data)
        df.to_csv(csv_content, index=False)
        csv_content.seek(0)
        return SimpleUploadedFile(
            'test_data.csv',
            csv_content.getvalue().encode('utf-8'),
            content_type='text/csv'
        )

    def test_parse_and_clean_file_success(self):
        """Test successful CSV parsing and cleaning."""
        test_data = [
            {
                'MLSNumber': 'MLS001',
                'ClosePrice': '$500,000',
                'CloseDate': '2023-01-15',
                'SqFtLivArea': '2000',
                'SqFtTotal': '2200'
            },
            {
                'MLSNumber': 'MLS002',
                'ClosePrice': '$450000',
                'CloseDate': '2023-02-20',
                'SqFtLivArea': '1800',
                'SqFtTotal': '2000'
            }
        ]

        csv_file = self.create_test_csv(test_data)
        df, rows_excluded = parse_and_clean_file(csv_file)

        self.assertEqual(len(df), 2)
        self.assertEqual(rows_excluded, 0)
        self.assertEqual(df.iloc[0]['ClosePrice'], 500000.0)
        self.assertEqual(df.iloc[0]['price_per_sf'], 250.0)  # 500000 / 2000

    def test_parse_and_clean_file_with_exclusions(self):
        """Test CSV parsing with invalid data that gets excluded."""
        test_data = [
            {
                'MLSNumber': 'MLS001',
                'ClosePrice': '$500,000',
                'CloseDate': '2023-01-15',
                'SqFtLivArea': '2000',
                'SqFtTotal': '2200'
            },
            {
                'MLSNumber': 'MLS002',
                'ClosePrice': '',  # Invalid price
                'CloseDate': '2023-02-20',
                'SqFtLivArea': '1800',
                'SqFtTotal': '2000'
            },
            {
                'MLSNumber': 'MLS003',
                'ClosePrice': '$300000',
                'CloseDate': '',  # Invalid date
                'SqFtLivArea': '1500',
                'SqFtTotal': '1700'
            }
        ]

        csv_file = self.create_test_csv(test_data)
        df, rows_excluded = parse_and_clean_file(csv_file)

        self.assertEqual(len(df), 1)
        self.assertEqual(rows_excluded, 2)

    def test_analyze_sales_dataframe(self):
        """Test sales dataframe analysis."""
        # Create test dataframe
        test_data = {
            'ClosePrice': [500000, 510000, 520000, 480000],
            'CloseDate': pd.to_datetime(['2023-01-15', '2023-02-20', '2023-03-10', '2023-01-25']),
            'price_per_sf': [250, 255, 260, 240],
            'year': [2023, 2023, 2023, 2023],
            'year_month': ['2023-01', '2023-02', '2023-03', '2023-01']
        }
        df = pd.DataFrame(test_data)

        results = analyze_sales_dataframe(df, n_last_months=12)

        self.assertIn('monthly_table', results)
        self.assertIn('yearly_table', results)
        self.assertIn('time_adjustments', results)

        monthly_table = results['monthly_table']
        self.assertTrue(len(monthly_table) > 0)

        # Check that we have month-over-month changes
        for month in monthly_table:
            if 'median_pps_pct_change' in month:
                self.assertIsInstance(month['median_pps_pct_change'], (int, float, type(None)))


class TimeAdjustmentTestCase(TestCase):
    """Test cases for time adjustment calculations."""

    def setUp(self):
        """Set up test data for time adjustments."""
        self.monthly_data = [
            {'year_month': '2023-01', 'median_close': 500000, 'median_pps': 250},
            {'year_month': '2023-02', 'median_close': 510000, 'median_pps': 255},
            {'year_month': '2023-03', 'median_close': 520000, 'median_pps': 260},
            {'year_month': '2023-04', 'median_close': 515000, 'median_pps': 257},
            {'year_month': '2023-05', 'median_close': 525000, 'median_pps': 262}
        ]

    def test_calculate_monthly_adjustment(self):
        """Test monthly median adjustment calculation."""
        effective_date = date(2023, 5, 15)
        sale_date = date(2023, 2, 10)

        adjustment = calculate_monthly_adjustment(
            self.monthly_data, effective_date, sale_date, 'median_close'
        )

        self.assertIsNotNone(adjustment)
        self.assertIsInstance(adjustment, float)
        # Should be positive since prices increased from Feb to May
        self.assertGreater(adjustment, 0)

    def test_calculate_linear_trendline_adjustment(self):
        """Test linear trendline adjustment calculation."""
        effective_date = date(2023, 5, 15)
        sale_date = date(2023, 2, 10)

        adjustment = calculate_linear_trendline_adjustment(
            self.monthly_data, effective_date, sale_date, 'median_close'
        )

        self.assertIsNotNone(adjustment)
        self.assertIsInstance(adjustment, float)

    def test_calculate_polynomial_trendline_adjustment(self):
        """Test polynomial trendline adjustment calculation."""
        effective_date = date(2023, 5, 15)
        sale_date = date(2023, 2, 10)

        adjustment = calculate_polynomial_trendline_adjustment(
            self.monthly_data, effective_date, sale_date, 'median_close', degree=4
        )

        self.assertIsNotNone(adjustment)
        self.assertIsInstance(adjustment, float)

    def test_process_time_adjustments(self):
        """Test complete time adjustment processing."""
        upload_results = {'monthly_table': self.monthly_data}
        effective_date = date(2023, 5, 15)
        comparable_sales = [
            (date(2023, 2, 10), 480000, 1920, '123 Test St'),
            (date(2023, 3, 20), 495000, 1980, '456 Oak Ave')
        ]

        results = process_time_adjustments(
            upload_results, effective_date, comparable_sales
        )

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn('adjustments', result)
            adjustments = result['adjustments']
            self.assertIn('monthly_price', adjustments)
            self.assertIn('linear_price', adjustments)
            self.assertIn('polynomial_price', adjustments)

    def test_generate_trendline_data(self):
        """Test trendline data generation for charts."""
        trendlines = generate_trendline_data(self.monthly_data, 'median_close')

        self.assertIn('linear', trendlines)
        self.assertIn('polynomial', trendlines)
        self.assertIsInstance(trendlines['linear'], list)
        self.assertIsInstance(trendlines['polynomial'], list)


class FormTestCase(TestCase):
    """Test cases for Django forms."""

    def test_csv_upload_form_valid(self):
        """Test valid CSV upload form."""
        csv_content = "ClosePrice,CloseDate,SqFtLivArea\n500000,2023-01-15,2000"
        csv_file = SimpleUploadedFile(
            'test.csv',
            csv_content.encode('utf-8'),
            content_type='text/csv'
        )

        form_data = {
            'address': '123 Test St',
            'save_sales_to_db': True
        }
        form = CSVUploadForm(data=form_data, files={'file': csv_file})

        self.assertTrue(form.is_valid())

    def test_csv_upload_form_invalid_file(self):
        """Test invalid file type in upload form."""
        txt_file = SimpleUploadedFile(
            'test.txt',
            b'This is not a CSV file',
            content_type='text/plain'
        )

        form_data = {'address': '123 Test St'}
        form = CSVUploadForm(data=form_data, files={'file': txt_file})

        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

    def test_time_adjustment_form(self):
        """Test time adjustment form validation."""
        form_data = {'effective_date': '2023-06-01'}
        form = TimeAdjustmentForm(data=form_data)

        self.assertTrue(form.is_valid())

        # Test future date validation
        future_form_data = {'effective_date': '2025-12-31'}
        future_form = TimeAdjustmentForm(data=future_form_data)
        self.assertFalse(future_form.is_valid())

    def test_comparable_sale_formset(self):
        """Test comparable sale formset."""
        formset_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '20',
            'form-0-sale_date': '2023-03-15',
            'form-0-sale_price': '475000',
            'form-0-square_footage': '1900',
            'form-0-address': '456 Comp St',
            'form-1-sale_date': '2023-04-20',
            'form-1-sale_price': '485000',
            'form-1-square_footage': '1950',
            'form-1-address': '789 Main Ave'
        }

        formset = ComparableSaleFormSet(data=formset_data)
        self.assertTrue(formset.is_valid())


class ViewTestCase(TestCase):
    """Test cases for Django views."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.upload = Upload.objects.create(
            address='123 Test St, Test City, TS',
            original_filename='test_data.csv',
            uploaded_by=self.user,
            rows_processed=100,
            results_summary={
                'monthly_table': [
                    {'year_month': '2023-01', 'median_close': 500000, 'median_pps': 250, 'n': 10}
                ]
            }
        )

    def test_analysis_list_view(self):
        """Test analysis list view."""
        url = reverse('marketanalysis:analysis_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '123 Test St, Test City, TS')
        self.assertContains(response, 'test_data.csv')

    def test_upload_view_get(self):
        """Test upload view GET request."""
        url = reverse('marketanalysis:upload')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload MLS Data')

    def test_analysis_detail_view(self):
        """Test analysis detail view."""
        url = reverse('marketanalysis:view_analysis', kwargs={'pk': self.upload.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '123 Test St, Test City, TS')

    def test_time_adjustment_view_get(self):
        """Test time adjustment view GET request."""
        url = reverse('marketanalysis:time_adjustment', kwargs={'pk': self.upload.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Time Adjustment Analysis')

    def test_nonexistent_upload_404(self):
        """Test 404 response for nonexistent upload."""
        url = reverse('marketanalysis:view_analysis', kwargs={'pk': 9999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class IntegrationTestCase(TestCase):
    """Integration tests for complete workflows."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def create_sample_csv(self):
        """Create a sample CSV file for testing."""
        csv_content = """MLSNumber,ClosePrice,CloseDate,SqFtLivArea,SqFtTotal,StreetName,City
MLS001,$500000,2023-01-15,2000,2200,Test Street,Test City
MLS002,$510000,2023-02-20,1800,2000,Oak Avenue,Test City
MLS003,$495000,2023-03-10,1900,2100,Main Street,Test City
MLS004,$520000,2023-04-05,2100,2300,Pine Road,Test City"""

        return SimpleUploadedFile(
            'sample_data.csv',
            csv_content.encode('utf-8'),
            content_type='text/csv'
        )

    def test_complete_upload_and_analysis_workflow(self):
        """Test complete workflow from upload to analysis."""
        # Step 1: Upload CSV file
        csv_file = self.create_sample_csv()
        upload_url = reverse('marketanalysis:upload')

        upload_data = {
            'address': '123 Subject Property St',
            'file': csv_file,
            'save_sales_to_db': True
        }

        response = self.client.post(upload_url, upload_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify upload was created
        upload = Upload.objects.first()
        self.assertIsNotNone(upload)
        self.assertEqual(upload.address, '123 Subject Property St')
        self.assertEqual(upload.rows_processed, 4)

        # Step 2: View analysis
        analysis_url = reverse('marketanalysis:view_analysis', kwargs={'pk': upload.pk})
        response = self.client.get(analysis_url)
        self.assertEqual(response.status_code, 200)

        # Step 3: Create time adjustment analysis
        time_adj_url = reverse('marketanalysis:time_adjustment', kwargs={'pk': upload.pk})

        time_adj_data = {
            'effective_date': '2023-05-01',
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '20',
            'form-0-sale_date': '2023-02-10',
            'form-0-sale_price': '480000',
            'form-0-square_footage': '1850',
            'form-0-address': '456 Comparable St',
            'form-1-sale_date': '2023-03-20',
            'form-1-sale_price': '495000',
            'form-1-square_footage': '1900',
            'form-1-address': '789 Another Comp Ave'
        }

        response = self.client.post(time_adj_url, time_adj_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify time adjustment analysis was created
        analysis = TimeAdjustmentAnalysis.objects.first()
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.comparable_sales.count(), 2)
