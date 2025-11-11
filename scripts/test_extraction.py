#!/usr/bin/env python
"""Test script for extraction service."""

import os
import sys
import django

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import uuid
from extraction.services import create_extraction_job
from extraction.models import ExtractionJob, ExtractionResult


def test_extraction():
    """Test extraction with a sample schema."""

    print("Creating test extraction job...")

    # Sample schema for contract extraction
    schema_definition = [
        {
            'name': 'contract_number',
            'description': 'The contract identification number',
            'type': 'string',
            'required': True,
            'example': 'CONTRACT-2024-001'
        },
        {
            'name': 'contract_value',
            'description': 'Total contract value in dollars',
            'type': 'number',
            'required': True,
            'example': 150000.00
        },
        {
            'name': 'start_date',
            'description': 'Contract start date in YYYY-MM-DD format',
            'type': 'string',
            'required': False,
            'example': '2024-01-15'
        },
        {
            'name': 'end_date',
            'description': 'Contract end date in YYYY-MM-DD format',
            'type': 'string',
            'required': False,
            'example': '2024-12-31'
        },
        {
            'name': 'contractor_name',
            'description': 'Name of the contractor',
            'type': 'string',
            'required': True,
            'example': 'ABC Construction Ltd'
        },
        {
            'name': 'project_description',
            'description': 'Brief description of the project',
            'type': 'string',
            'required': False,
            'example': 'Residential building construction'
        }
    ]

    # Create a test document ID (in real scenario, this would be from ingestion service)
    test_document_id = str(uuid.uuid4())

    print(f"Test document ID: {test_document_id}")
    print(f"Schema fields: {len(schema_definition)}")

    # Create extraction job
    job = create_extraction_job(
        document_id=test_document_id,
        schema_name='ContractDetails',
        schema_description='Extract key information from construction contracts',
        fields=schema_definition,
        context='This is a construction contract document containing project details, contractor information, and financial terms.',
        llm_provider='openai',
        llm_model='gpt-4',
        temperature=0.1,
        total_passes=2,
        project_id=str(uuid.uuid4()),
        tags=['test', 'contract', 'construction']
    )

    print(f"\nExtraction job created: {job.id}")
    print(f"Status: {job.status}")
    print(f"Schema: {job.schema_name}")
    print(f"Total fields: {job.total_fields}")
    print(f"Extracted fields: {job.extracted_fields}")

    if job.confidence_score:
        print(f"Confidence score: {job.confidence_score:.2%}")

    if job.error_message:
        print(f"Error: {job.error_message}")

    # Print results
    results = ExtractionResult.objects.filter(job=job).order_by('field_name')

    if results:
        print(f"\n{'-' * 80}")
        print("EXTRACTION RESULTS:")
        print(f"{'-' * 80}")

        for result in results:
            print(f"\nField: {result.field_name}")
            print(f"  Type: {result.field_type}")
            print(f"  Value: {result.value}")
            print(f"  Confidence: {result.confidence:.2%}")
            print(f"  Valid: {result.is_valid}")

            if result.source_text:
                print(f"  Source: {result.source_text[:100]}...")

    # Print validation history
    if job.validation_history.exists():
        print(f"\n{'-' * 80}")
        print("VALIDATION HISTORY:")
        print(f"{'-' * 80}")

        for history in job.validation_history.all():
            print(f"\nPass {history.pass_number} - {history.action}")
            print(f"  Valid: {history.is_valid}")

            if history.validation_errors:
                print(f"  Errors: {history.validation_errors}")

            if history.repaired_fields:
                print(f"  Repaired: {', '.join(history.repaired_fields)}")

    print(f"\n{'-' * 80}")
    print(f"Total tokens used: {job.total_tokens}")
    print(f"  Prompt tokens: {job.prompt_tokens}")
    print(f"  Completion tokens: {job.completion_tokens}")
    print(f"{'-' * 80}\n")

    return job


if __name__ == '__main__':
    print("=" * 80)
    print("EXTRACTION SERVICE TEST")
    print("=" * 80)
    print()

    try:
        job = test_extraction()

        if job.status == 'completed':
            print("✓ Test completed successfully!")
        else:
            print(f"✗ Test ended with status: {job.status}")

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
