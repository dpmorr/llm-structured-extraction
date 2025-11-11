"""Tests for extraction service."""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
import uuid

from .models import ExtractionJob, ExtractionResult, ValidationHistory
from .services import ExtractionService, create_extraction_job


class ExtractionJobModelTest(TestCase):
    """Test ExtractionJob model."""

    def setUp(self):
        """Set up test data."""
        self.schema_definition = {
            'name': 'TestSchema',
            'description': 'Test schema',
            'fields': [
                {
                    'name': 'field1',
                    'description': 'First field',
                    'type': 'string',
                    'required': True,
                },
                {
                    'name': 'field2',
                    'description': 'Second field',
                    'type': 'number',
                    'required': False,
                }
            ]
        }

    def test_create_extraction_job(self):
        """Test creating an extraction job."""
        job = ExtractionJob.objects.create(
            document_id=uuid.uuid4(),
            schema_name='TestSchema',
            schema_description='Test schema description',
            schema_definition=self.schema_definition,
        )

        self.assertIsNotNone(job.id)
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.current_pass, 0)
        self.assertEqual(job.schema_name, 'TestSchema')

    def test_extraction_job_str(self):
        """Test string representation."""
        job = ExtractionJob.objects.create(
            document_id=uuid.uuid4(),
            schema_name='TestSchema',
            schema_description='Test',
            schema_definition=self.schema_definition,
        )

        str_repr = str(job)
        self.assertIn('TestSchema', str_repr)
        self.assertIn('pending', str_repr)


class ExtractionResultModelTest(TestCase):
    """Test ExtractionResult model."""

    def setUp(self):
        """Set up test data."""
        self.job = ExtractionJob.objects.create(
            document_id=uuid.uuid4(),
            schema_name='TestSchema',
            schema_description='Test',
            schema_definition={'fields': []},
        )

    def test_create_extraction_result(self):
        """Test creating an extraction result."""
        result = ExtractionResult.objects.create(
            job=self.job,
            field_name='test_field',
            field_type='string',
            value='test value',
            confidence=0.95,
        )

        self.assertIsNotNone(result.id)
        self.assertEqual(result.field_name, 'test_field')
        self.assertEqual(result.confidence, 0.95)
        self.assertTrue(result.is_valid)

    def test_unique_together_constraint(self):
        """Test unique together constraint."""
        ExtractionResult.objects.create(
            job=self.job,
            field_name='test_field',
            field_type='string',
            value='test value',
            confidence=0.95,
            extraction_pass=1,
        )

        # Should raise error for duplicate
        with self.assertRaises(Exception):
            ExtractionResult.objects.create(
                job=self.job,
                field_name='test_field',
                field_type='string',
                value='test value 2',
                confidence=0.85,
                extraction_pass=1,
            )


class ExtractionJobAPITest(APITestCase):
    """Test Extraction Job API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.schema_definition = {
            'fields': [
                {
                    'name': 'field1',
                    'description': 'First field',
                    'type': 'string',
                    'required': True,
                }
            ]
        }

    def test_list_jobs(self):
        """Test listing extraction jobs."""
        # Create a job
        ExtractionJob.objects.create(
            document_id=uuid.uuid4(),
            schema_name='TestSchema',
            schema_description='Test',
            schema_definition=self.schema_definition,
        )

        response = self.client.get('/api/jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_job_detail(self):
        """Test getting job detail."""
        job = ExtractionJob.objects.create(
            document_id=uuid.uuid4(),
            schema_name='TestSchema',
            schema_description='Test',
            schema_definition=self.schema_definition,
        )

        response = self.client.get(f'/api/jobs/{job.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['schema_name'], 'TestSchema')

    def test_filter_by_status(self):
        """Test filtering jobs by status."""
        ExtractionJob.objects.create(
            document_id=uuid.uuid4(),
            schema_name='Test1',
            schema_description='Test',
            schema_definition=self.schema_definition,
            status='pending',
        )
        ExtractionJob.objects.create(
            document_id=uuid.uuid4(),
            schema_name='Test2',
            schema_description='Test',
            schema_definition=self.schema_definition,
            status='completed',
        )

        response = self.client.get('/api/jobs/?status=completed')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'completed')


class ValidationHistoryTest(TestCase):
    """Test ValidationHistory model."""

    def setUp(self):
        """Set up test data."""
        self.job = ExtractionJob.objects.create(
            document_id=uuid.uuid4(),
            schema_name='TestSchema',
            schema_description='Test',
            schema_definition={'fields': []},
        )

    def test_create_validation_history(self):
        """Test creating validation history."""
        history = ValidationHistory.objects.create(
            job=self.job,
            action='validate',
            pass_number=1,
            is_valid=True,
        )

        self.assertIsNotNone(history.id)
        self.assertEqual(history.action, 'validate')
        self.assertTrue(history.is_valid)

    def test_repair_history(self):
        """Test repair history."""
        history = ValidationHistory.objects.create(
            job=self.job,
            action='repair',
            pass_number=2,
            is_valid=True,
            repaired_fields=['field1', 'field2'],
            repair_description='Repaired 2 fields',
        )

        self.assertEqual(len(history.repaired_fields), 2)
        self.assertEqual(history.repair_description, 'Repaired 2 fields')
