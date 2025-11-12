# Extraction Service

Django-based extraction service for structured data extraction from documents using LLMs.

## Features

- Multi-Provider LLM Support: Uses litellm for OpenAI, Anthropic Claude, and AWS Bedrock
- Structured Outputs: Uses instructor library with Pydantic for type-safe structured extraction
- Multi-Pass Validation: Automatic validation and repair of extraction results
- Custom Schemas: Accept any extraction schema definition at runtime
- PostgreSQL Storage: Persistent storage of extraction jobs and results
- Django REST Framework: Full REST API with browsable interface
- Django Admin: Rich admin interface for monitoring and management

## Architecture

```
extraction/
├── config/              # Django configuration
│   ├── settings.py     # Settings with LLM configuration
│   └── urls.py         # Root URL routing
├── extraction/          # Main app
│   ├── models.py       # ExtractionJob, ExtractionResult, ValidationHistory
│   ├── serializers.py  # DRF serializers
│   ├── views.py        # API ViewSets
│   ├── services.py     # Core extraction logic with instructor
│   ├── urls.py         # App URL routing
│   └── admin.py        # Django admin configuration
└── manage.py           # Django management
```

## Setup

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# LLM Provider (openai, anthropic, or bedrock)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.1

# API Keys
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here

# AWS for Bedrock
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1

# Database
POSTGRES_DB=extraction
POSTGRES_USER=extraction
POSTGRES_PASSWORD=changeme
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver 0.0.0.0:8001
```

### Docker

```bash
docker build -t document-extraction .
docker run -p 8001:8001 --env-file .env document-extraction
```

## API Endpoints

### Create Extraction Job

```bash
POST /api/jobs/
Content-Type: application/json

{
  "document_id": "uuid-here",
  "schema_name": "ContractDetails",
  "schema_description": "Extract key contract information",
  "schema_definition": {
    "fields": [
      {
        "name": "contract_number",
        "description": "The contract identification number",
        "type": "string",
        "required": true
      },
      {
        "name": "contract_value",
        "description": "Total contract value in dollars",
        "type": "number",
        "required": true
      },
      {
        "name": "start_date",
        "description": "Contract start date",
        "type": "string",
        "required": false
      }
    ]
  },
  "context": "This is a business contract",
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "temperature": 0.1,
  "total_passes": 2,
  "project_id": "uuid-here",
  "tags": ["contract", "important"]
}
```

### Extract (Simplified Endpoint)

```bash
POST /api/extractions/
Content-Type: application/json

{
  "document_id": "uuid-here",
  "schema_name": "ContractDetails",
  "schema_description": "Extract key contract information",
  "fields": [
    {
      "name": "contract_number",
      "description": "The contract identification number",
      "type": "string",
      "required": true
    }
  ],
  "context": "Optional context",
  "llm_provider": "openai",
  "llm_model": "gpt-4"
}
```

### Get Job Status

```bash
GET /api/jobs/{job_id}/
```

### Get Job Results

```bash
GET /api/jobs/{job_id}/results/
```

### Retry Failed Job

```bash
POST /api/jobs/{job_id}/retry/
```

### List Jobs

```bash
GET /api/jobs/
GET /api/jobs/?document_id=uuid-here
GET /api/jobs/?status=completed
GET /api/jobs/?project_id=uuid-here
```

### Get Statistics

```bash
GET /api/jobs/stats/
```

## Models

### ExtractionJob

Tracks extraction job lifecycle:
- Document reference
- Schema definition
- Status (pending, processing, validating, repairing, completed, failed)
- Multi-pass configuration
- LLM configuration and usage tracking
- Results metadata

### ExtractionResult

Individual field extraction results:
- Field name, type, and value
- Confidence score
- Source text snippet
- Validation status
- Pass tracking

### ValidationHistory

Audit trail of validation and repair attempts:
- Action type (validate, repair, retry)
- Pass number
- Validation errors
- Repaired fields

## Extraction Service

The `ExtractionService` class handles:

1. **Dynamic Schema Building**: Converts JSON schema to Pydantic models
2. **Document Retrieval**: Fetches document text from ingestion service
3. **LLM Extraction**: Uses instructor + litellm for structured extraction
4. **Validation**: Checks confidence thresholds and required fields
5. **Repair**: Re-extracts invalid fields with focused prompts
6. **Multi-Pass Processing**: Iterates until validation passes or max attempts reached

### Example Usage

```python
from extraction.services import create_extraction_job

job = create_extraction_job(
    document_id="abc-123",
    schema_name="ContractDetails",
    schema_description="Extract contract information",
    fields=[
        {
            "name": "contract_number",
            "description": "Contract ID",
            "type": "string",
            "required": True
        }
    ],
    context="Business contract",
    llm_provider="openai",
    llm_model="gpt-4",
    temperature=0.1,
    total_passes=2
)
```

## LLM Provider Configuration

### OpenAI

```python
LLM_PROVIDER=openai
LLM_MODEL=gpt-4  # or gpt-3.5-turbo
OPENAI_API_KEY=sk-...
```

### Anthropic Claude

```python
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-opus-20240229  # or claude-3-sonnet, claude-3-haiku
ANTHROPIC_API_KEY=sk-ant-...
```

### AWS Bedrock

```python
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-v2  # or other Bedrock models
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

## Admin Interface

Access the Django admin at `/admin/` to:

- View and manage extraction jobs
- Inspect extraction results
- Review validation history
- Monitor system statistics
- Filter and search jobs

## Integration with Shared Schemas

The service uses shared Pydantic schemas from `/shared/schemas.py`:

- `ExtractionRequest`
- `ExtractionResponse`
- `ExtractionField`
- `ExtractionSchema`
- `ProcessingStatus`

## Error Handling

- Automatic retry for failed extractions (configurable max retries)
- Detailed error messages stored in job records
- Validation history for debugging
- Token usage tracking for cost monitoring

## Performance Considerations

- Async extraction processing (can be enhanced with Celery)
- Configurable timeout settings
- Token usage limits
- Confidence thresholds
- Multi-pass optimization

## Testing

```bash
# Run tests
python manage.py test extraction

# Create test data
python manage.py shell
>>> from extraction.services import create_extraction_job
>>> # Create test jobs
```

## Development

```bash
# Make migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Run development server
python manage.py runserver 0.0.0.0:8001
```

## Use Cases

The extraction service supports the following document types:

**Financial Services**
- Invoices, receipts, and purchase orders
- Loan applications and financial statements
- Investment reports and prospectuses

**Legal Industry**
- Contracts and agreements
- Legal briefs and case documents
- Regulatory filings and compliance documents

**Healthcare**
- Medical records and patient forms
- Clinical trial documents
- Research papers and medical literature

**Business Operations**
- Employee forms and HR documents
- Business reports and presentations
- Vendor contracts and purchase agreements

**Research & Academia**
- Research papers
- Survey responses and questionnaires
- Academic publications and citations

**Government & Public Sector**
- Permit applications and regulatory forms
- Public records and filings
- Policy documents and legislation
