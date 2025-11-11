# Extraction Service - Quick Start Guide

## Setup (5 minutes)

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```bash
OPENAI_API_KEY=sk-your-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 2. Run Migrations

```bash
python manage.py migrate
```

### 3. Create Admin User

```bash
python manage.py createsuperuser
```

### 4. Start Server

```bash
python manage.py runserver 0.0.0.0:8001
```

## Quick Test

### Option 1: Using the API

```bash
curl -X POST http://localhost:8001/api/extractions/ \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "schema_name": "ContractDetails",
    "schema_description": "Extract contract information",
    "fields": [
      {
        "name": "contract_number",
        "description": "Contract ID number",
        "type": "string",
        "required": true
      },
      {
        "name": "total_value",
        "description": "Total contract value in dollars",
        "type": "number",
        "required": true
      }
    ],
    "llm_provider": "openai",
    "llm_model": "gpt-4"
  }'
```

### Option 2: Using the Test Script

```bash
python scripts/test_extraction.py
```

### Option 3: Using Django Admin

1. Visit http://localhost:8001/admin/
2. Log in with superuser credentials
3. Go to "Extraction jobs"
4. Click "Add extraction job"

## API Endpoints

```
POST   /api/extractions/           # Create extraction (simplified)
POST   /api/jobs/                  # Create extraction job (full)
GET    /api/jobs/                  # List all jobs
GET    /api/jobs/{id}/             # Get job details
GET    /api/jobs/{id}/results/     # Get extraction results
POST   /api/jobs/{id}/retry/       # Retry failed job
GET    /api/jobs/stats/            # Get statistics
GET    /api/results/               # List all results
```

## Common Operations

### Check Job Status

```bash
curl http://localhost:8001/api/jobs/{job_id}/
```

### Get Results

```bash
curl http://localhost:8001/api/jobs/{job_id}/results/
```

### List Recent Jobs

```bash
curl http://localhost:8001/api/jobs/?limit=10
```

### Filter by Status

```bash
curl http://localhost:8001/api/jobs/?status=completed
```

### Get Statistics

```bash
curl http://localhost:8001/api/jobs/stats/
```

## LLM Providers

### OpenAI (Default)

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...
```

Models: `gpt-4`, `gpt-3.5-turbo`

### Anthropic Claude

```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-opus-20240229
ANTHROPIC_API_KEY=sk-ant-...
```

Models: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`

### AWS Bedrock

```bash
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-v2
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

## Docker

```bash
# Build
docker build -t propclaim-extraction .

# Run
docker run -p 8001:8001 --env-file .env propclaim-extraction
```

## Troubleshooting

### "No module named 'instructor'"
```bash
pip install -r requirements.txt
```

### "relation does not exist"
```bash
python manage.py migrate
```

### "Invalid API key"
Check your `.env` file and ensure the correct API key is set.

### Document text not available
The service tries to fetch document text from the ingestion service. If unavailable, it will use a placeholder. Configure `INGESTION_SERVICE_URL` in settings.

## Next Steps

1. Integrate with ingestion service for document text
2. Add Celery for async processing
3. Configure production database
4. Set up monitoring and logging
5. Add authentication/authorization

## Support

For issues or questions, refer to the full README.md
