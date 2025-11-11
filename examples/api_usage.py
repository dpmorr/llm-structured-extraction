"""Example API usage for extraction service."""

import requests
import json
import uuid
import time

# Configuration
BASE_URL = "http://localhost:8001"
API_URL = f"{BASE_URL}/api"


def create_extraction_job_full():
    """Create extraction job using full job endpoint."""
    url = f"{API_URL}/jobs/"

    payload = {
        "document_id": str(uuid.uuid4()),
        "schema_name": "ContractDetails",
        "schema_description": "Extract key contract information from construction documents",
        "schema_definition": {
            "fields": [
                {
                    "name": "contract_number",
                    "description": "The unique contract identification number",
                    "type": "string",
                    "required": True,
                    "example": "CONTRACT-2024-001"
                },
                {
                    "name": "contract_value",
                    "description": "Total contract value in dollars",
                    "type": "number",
                    "required": True,
                    "example": 250000.00
                },
                {
                    "name": "start_date",
                    "description": "Contract start date in YYYY-MM-DD format",
                    "type": "string",
                    "required": False
                },
                {
                    "name": "contractor_name",
                    "description": "Name of the contracting company",
                    "type": "string",
                    "required": True
                },
                {
                    "name": "payment_terms",
                    "description": "Payment terms and schedule",
                    "type": "string",
                    "required": False
                }
            ]
        },
        "context": "This is a construction contract for a residential building project.",
        "llm_provider": "openai",
        "llm_model": "gpt-4",
        "temperature": 0.1,
        "total_passes": 2,
        "project_id": str(uuid.uuid4()),
        "tags": ["construction", "contract", "residential"]
    }

    response = requests.post(url, json=payload)

    if response.status_code == 201:
        job = response.json()
        print("✓ Extraction job created successfully!")
        print(f"  Job ID: {job['id']}")
        print(f"  Status: {job['status']}")
        print(f"  Schema: {job['schema_name']}")
        return job['id']
    else:
        print(f"✗ Failed to create job: {response.status_code}")
        print(f"  Error: {response.text}")
        return None


def create_extraction_simplified():
    """Create extraction using simplified endpoint."""
    url = f"{API_URL}/extractions/"

    payload = {
        "document_id": str(uuid.uuid4()),
        "schema_name": "InvoiceDetails",
        "schema_description": "Extract invoice information",
        "fields": [
            {
                "name": "invoice_number",
                "description": "Invoice number",
                "type": "string",
                "required": True
            },
            {
                "name": "total_amount",
                "description": "Total invoice amount",
                "type": "number",
                "required": True
            },
            {
                "name": "due_date",
                "description": "Payment due date",
                "type": "string",
                "required": False
            }
        ],
        "llm_provider": "openai",
        "llm_model": "gpt-4"
    }

    response = requests.post(url, json=payload)

    if response.status_code == 201:
        result = response.json()
        print("✓ Extraction completed!")
        print(f"  Extraction ID: {result['extraction_id']}")
        print(f"  Status: {result['status']}")
        print(f"  Confidence: {result.get('confidence_score', 'N/A')}")
        return result['extraction_id']
    else:
        print(f"✗ Extraction failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return None


def get_job_status(job_id):
    """Get extraction job status."""
    url = f"{API_URL}/jobs/{job_id}/"
    response = requests.get(url)

    if response.status_code == 200:
        job = response.json()
        print(f"\nJob Status: {job['status']}")
        print(f"  Schema: {job['schema_name']}")
        print(f"  Progress: {job['extracted_fields']}/{job['total_fields']} fields")

        if job['confidence_score']:
            print(f"  Confidence: {job['confidence_score']:.2%}")

        if job['error_message']:
            print(f"  Error: {job['error_message']}")

        return job
    else:
        print(f"Failed to get job status: {response.status_code}")
        return None


def get_job_results(job_id):
    """Get extraction results."""
    url = f"{API_URL}/jobs/{job_id}/results/"
    response = requests.get(url)

    if response.status_code == 200:
        results = response.json()
        print(f"\nExtraction Results ({len(results)} fields):")
        print("-" * 80)

        for result in results:
            print(f"\n{result['field_name']} ({result['field_type']})")
            print(f"  Value: {result['value']}")
            print(f"  Confidence: {result['confidence']:.2%}")
            print(f"  Valid: {result['is_valid']}")

        return results
    else:
        print(f"Failed to get results: {response.status_code}")
        return None


def list_jobs(status=None, limit=10):
    """List extraction jobs."""
    url = f"{API_URL}/jobs/"
    params = {"limit": limit}

    if status:
        params["status"] = status

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        jobs = data.get('results', [])

        print(f"\nFound {data.get('count', 0)} jobs (showing {len(jobs)}):")
        print("-" * 80)

        for job in jobs:
            print(f"\n{job['id']}")
            print(f"  Schema: {job['schema_name']}")
            print(f"  Status: {job['status']}")
            print(f"  Created: {job['created_at']}")

        return jobs
    else:
        print(f"Failed to list jobs: {response.status_code}")
        return None


def retry_failed_job(job_id):
    """Retry a failed extraction job."""
    url = f"{API_URL}/jobs/{job_id}/retry/"
    response = requests.post(url)

    if response.status_code == 200:
        job = response.json()
        print(f"✓ Job retry initiated")
        print(f"  Status: {job['status']}")
        return job
    else:
        print(f"✗ Retry failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return None


def get_stats():
    """Get extraction statistics."""
    url = f"{API_URL}/jobs/stats/"
    response = requests.get(url)

    if response.status_code == 200:
        stats = response.json()
        print("\nExtraction Service Statistics:")
        print("-" * 80)
        print(f"  Total jobs: {stats.get('total_jobs', 0)}")
        print(f"  Pending: {stats.get('pending', 0)}")
        print(f"  Processing: {stats.get('processing', 0)}")
        print(f"  Completed: {stats.get('completed', 0)}")
        print(f"  Failed: {stats.get('failed', 0)}")

        if stats.get('average_confidence'):
            print(f"  Avg confidence: {stats['average_confidence']:.2%}")

        if stats.get('total_tokens_used'):
            print(f"  Total tokens: {stats['total_tokens_used']:,}")

        return stats
    else:
        print(f"Failed to get stats: {response.status_code}")
        return None


def wait_for_completion(job_id, timeout=300, interval=5):
    """Wait for job to complete."""
    print(f"\nWaiting for job {job_id} to complete...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        job = get_job_status(job_id)

        if job:
            status = job['status']

            if status in ['completed', 'failed']:
                print(f"\n✓ Job finished with status: {status}")
                return job

            print(f"  Status: {status} (waiting...)")

        time.sleep(interval)

    print("\n✗ Timeout waiting for job completion")
    return None


def main():
    """Run example API usage."""
    print("=" * 80)
    print("EXTRACTION SERVICE API EXAMPLES")
    print("=" * 80)

    # Example 1: Create full extraction job
    print("\n[Example 1] Creating extraction job (full endpoint)...")
    job_id = create_extraction_job_full()

    if job_id:
        # Wait for completion
        job = wait_for_completion(job_id)

        if job and job['status'] == 'completed':
            # Get results
            get_job_results(job_id)

    # Example 2: Create simplified extraction
    print("\n\n[Example 2] Creating extraction (simplified endpoint)...")
    extraction_id = create_extraction_simplified()

    # Example 3: List jobs
    print("\n\n[Example 3] Listing recent jobs...")
    list_jobs(limit=5)

    # Example 4: Filter by status
    print("\n\n[Example 4] Listing completed jobs...")
    list_jobs(status='completed', limit=5)

    # Example 5: Get statistics
    print("\n\n[Example 5] Getting statistics...")
    get_stats()

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)


if __name__ == '__main__':
    main()
