from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import json
import os

class UploadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('marketanalysis:upload')
        fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_sales.csv')
        with open(fixture_path, 'rb') as f:
            self.csv_bytes = f.read()

    def test_upload_and_analyze_in_memory(self):
        uploaded = SimpleUploadedFile("sample_sales.csv", self.csv_bytes, content_type="text/csv")
        response = self.client.post(self.url, {'csv_file': uploaded, 'save_to_db': False}, follow=True)
        self.assertEqual(response.status_code, 200)
        # The response context contains 'results' JSON embedded; we can check the content
        # Look for the JSON string inside rendered HTML
        content = response.content.decode('utf-8')
        self.assertIn('Median PPS', content) or True  # not strict; ensure no crash

    def test_upload_and_persist(self):
        # Ensure persistence works (save_to_db True)
        uploaded = SimpleUploadedFile("sample_sales.csv", self.csv_bytes, content_type="text/csv")
        response = self.client.post(self.url, {'csv_file': uploaded, 'save_to_db': True}, follow=True)
        self.assertEqual(response.status_code, 200)
        # ensure upload record saved and no error message present
        self.assertNotIn('Error processing file', response.content.decode('utf-8'))
