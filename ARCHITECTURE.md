# Extraction Service - Architecture

## Overview

The extraction service is a Django-based microservice that provides structured data extraction from documents using Large Language Models (LLMs). It uses the instructor library for type-safe structured outputs and litellm for multi-provider LLM support.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT APPLICATIONS                      │
│         (Web UI, Mobile App, Other Microservices)           │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXTRACTION SERVICE                        │
│                     (Django + DRF)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              REST API Layer (views.py)               │  │
│  │  - ExtractionJobViewSet                             │  │
│  │  - ExtractionResultViewSet                          │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │         Serialization Layer (serializers.py)         │  │
│  │  - Request/Response validation                       │  │
│  │  - Data transformation                               │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │         Business Logic (services.py)                 │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │        ExtractionService                       │ │  │
│  │  │  - Schema building (Pydantic)                 │ │  │
│  │  │  - Document text retrieval                    │ │  │
│  │  │  - LLM extraction (instructor + litellm)      │ │  │
│  │  │  - Multi-pass validation & repair             │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │         Data Access Layer (models.py)                │  │
│  │  - ExtractionJob                                     │  │
│  │  - ExtractionResult                                  │  │
│  │  - ValidationHistory                                 │  │
│  └──────────────────┬───────────────────────────────────┘  │
└────────────────────┬┼┬────────────────────────────────────┘
                     │││
         ┌───────────┘││
         │            │└────────────┐
         │            │             │
         ▼            ▼             ▼
┌─────────────┐  ┌────────┐   ┌────────────┐
│ PostgreSQL  │  │  LLM   │   │ Ingestion  │
│  Database   │  │Provider│   │  Service   │
│             │  │        │   │            │
│ - Jobs      │  │OpenAI  │   │ Document   │
│ - Results   │  │Anthropic│  │   Text     │
│ - History   │  │Bedrock │   │            │
└─────────────┘  └────────┘   └────────────┘
```

## Component Details

### 1. REST API Layer (`views.py`)

**ExtractionJobViewSet**
- `POST /api/jobs/` - Create new extraction job
- `GET /api/jobs/` - List jobs with filtering
- `GET /api/jobs/{id}/` - Get job details
- `POST /api/jobs/{id}/retry/` - Retry failed job
- `GET /api/jobs/{id}/results/` - Get extraction results
- `POST /api/extractions/` - Simplified extraction endpoint
- `GET /api/jobs/stats/` - Get statistics

**ExtractionResultViewSet** (Read-only)
- `GET /api/results/` - List all results
- `GET /api/results/{id}/` - Get result details

### 2. Serialization Layer (`serializers.py`)

- **ExtractionJobSerializer** - Full job representation
- **ExtractionJobCreateSerializer** - Job creation with validation
- **ExtractionResultSerializer** - Individual result
- **ExtractionRequestSerializer** - Simplified request format
- **ExtractionResponseSerializer** - Simplified response format

### 3. Business Logic (`services.py`)

**ExtractionService Class**
```python
class ExtractionService:
    - __init__(job)
    - extract()                    # Main extraction
    - validate_results()           # Validate extracted data
    - repair_results()             # Fix invalid extractions
    - run_multi_pass_extraction()  # Orchestrate full process
    - _build_pydantic_model()      # Convert JSON schema to Pydantic
    - _get_document_text()         # Fetch from ingestion service
    - _build_extraction_prompt()   # Create LLM prompt
```

**Helper Functions**
- `create_extraction_job()` - Job factory
- `retry_extraction_job()` - Retry handler

### 4. Data Models (`models.py`)

**ExtractionJob**
- Primary entity tracking extraction lifecycle
- Stores schema definition, configuration, status
- Tracks LLM usage and performance metrics
- Relationships: results, validation_history

**ExtractionResult**
- Individual field extraction
- Stores value, confidence, source text
- Validation status per field
- Multi-pass tracking

**ValidationHistory**
- Audit trail for validation/repair
- Tracks errors and fixes
- LLM response storage

### 5. Admin Interface (`admin.py`)

Django admin with:
- Rich list displays with status badges
- Color-coded confidence scores
- Progress tracking
- Search and filtering
- Read-only fields for safety

## Data Flow

### Extraction Request Flow

```
1. API Request
   └─> Serializer validates input
       └─> create_extraction_job() called
           └─> ExtractionJob created in DB
               └─> ExtractionService initialized
                   └─> run_multi_pass_extraction()
                       │
                       ├─> Pass 1: extract()
                       │   ├─> Fetch document text
                       │   ├─> Build Pydantic model from schema
                       │   ├─> Call LLM via instructor + litellm
                       │   └─> Save ExtractionResults
                       │
                       ├─> validate_results()
                       │   ├─> Check confidence thresholds
                       │   ├─> Validate required fields
                       │   └─> Create ValidationHistory
                       │
                       ├─> If invalid: Pass 2: repair_results()
                       │   ├─> Re-extract invalid fields
                       │   ├─> Update ExtractionResults
                       │   └─> Create ValidationHistory
                       │
                       └─> Mark job as completed
                           └─> Return results to API
```

### Multi-Pass Validation & Repair

```
Pass 1 (Extract All)
  ↓
Validate
  ├─> All Valid → Complete ✓
  └─> Some Invalid
      ↓
Pass 2 (Repair Invalid)
  ↓
Validate
  ├─> All Valid → Complete ✓
  └─> Some Invalid
      ↓
Continue up to total_passes
  ↓
Complete (even if some invalid)
```

## Technology Stack

### Core Framework
- **Django 4.2+** - Web framework
- **Django REST Framework** - REST API
- **PostgreSQL** - Database

### LLM Integration
- **instructor** - Structured outputs with Pydantic
- **litellm** - Multi-provider LLM abstraction
- **pydantic** - Data validation and serialization

### Supported LLM Providers
- **OpenAI** - GPT-4, GPT-3.5
- **Anthropic** - Claude 3 (Opus, Sonnet, Haiku)
- **AWS Bedrock** - Various models

## Database Schema

### extraction_jobs
```sql
- id (UUID, PK)
- document_id (UUID, indexed)
- schema_name (VARCHAR)
- schema_description (TEXT)
- schema_definition (JSONB)
- status (VARCHAR, indexed)
- current_pass (INT)
- total_passes (INT)
- context (TEXT)
- llm_provider (VARCHAR)
- llm_model (VARCHAR)
- temperature (FLOAT)
- total_fields (INT)
- extracted_fields (INT)
- confidence_score (FLOAT)
- error_message (TEXT)
- retry_count (INT)
- max_retries (INT)
- prompt_tokens (INT)
- completion_tokens (INT)
- total_tokens (INT)
- project_id (UUID, indexed)
- tags (ARRAY)
- created_at (TIMESTAMP, indexed)
- updated_at (TIMESTAMP)
- completed_at (TIMESTAMP)
```

### extraction_results
```sql
- id (UUID, PK)
- job_id (UUID, FK, indexed)
- field_name (VARCHAR, indexed)
- field_type (VARCHAR)
- value (JSONB)
- confidence (FLOAT)
- source_text (TEXT)
- page_number (INT)
- is_valid (BOOLEAN)
- validation_errors (JSONB)
- extraction_pass (INT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

UNIQUE (job_id, field_name, extraction_pass)
```

### validation_history
```sql
- id (UUID, PK)
- job_id (UUID, FK, indexed)
- action (VARCHAR)
- pass_number (INT, indexed)
- is_valid (BOOLEAN)
- validation_errors (JSONB)
- repaired_fields (ARRAY)
- repair_description (TEXT)
- llm_response (JSONB)
- created_at (TIMESTAMP)
```

## Configuration

### Environment Variables

```bash
# Django
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS

# Database
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT

# LLM
LLM_PROVIDER (openai|anthropic|bedrock)
LLM_MODEL
LLM_TEMPERATURE
LLM_MAX_TOKENS

# API Keys
OPENAI_API_KEY
ANTHROPIC_API_KEY
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION

# Extraction
EXTRACTION_MAX_RETRIES
EXTRACTION_VALIDATION_PASSES
EXTRACTION_TIMEOUT

# Services
INGESTION_SERVICE_URL
```

## Scalability Considerations

### Current Architecture
- Synchronous processing in API request
- Single-threaded extraction
- Suitable for: Low-to-medium volume

### Future Enhancements
1. **Async Processing**
   - Add Celery for background tasks
   - Queue-based job processing
   - Webhook notifications

2. **Caching**
   - Redis for job status caching
   - Document text caching
   - Schema caching

3. **Load Balancing**
   - Multiple Django instances
   - Nginx/HAProxy for load distribution
   - Database connection pooling

4. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Error tracking (Sentry)

## Security

### Current Implementation
- CORS configuration
- CSRF protection
- Input validation via serializers
- SQL injection protection (ORM)

### Production Requirements
- API authentication (JWT/OAuth)
- Rate limiting
- API key management
- Audit logging
- Encryption at rest/transit

## Testing Strategy

### Unit Tests
- Model creation and constraints
- Serializer validation
- Service logic

### Integration Tests
- API endpoints
- Database operations
- LLM mocking

### End-to-End Tests
- Full extraction workflow
- Multi-pass validation
- Error handling

## Monitoring & Observability

### Key Metrics
- Jobs per status (pending, processing, completed, failed)
- Average confidence score
- Token usage
- Processing time per job
- Error rates
- Retry rates

### Logs
- Structured logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Contextual information (job_id, document_id)

## Deployment

### Docker
- Single container deployment
- Multi-stage builds
- Health checks
- Resource limits

### Docker Compose
- Service orchestration
- Database setup
- Network configuration

### Production
- Kubernetes deployment
- Horizontal pod autoscaling
- Rolling updates
- Blue-green deployments

## Integration Points

### Ingestion Service
- **Dependency**: Fetch document text
- **Endpoint**: `GET /api/documents/{id}/`
- **Fallback**: Placeholder text if unavailable

### Other Services
- Summary service (consumer)
- Anomaly detection (consumer)
- Claims service (consumer)

## Error Handling

### Retry Strategy
- Automatic retry for transient failures
- Exponential backoff (future)
- Max retry limit enforcement

### Failure Modes
- LLM API failures → Retry
- Invalid responses → Repair pass
- Timeout → Mark failed
- Schema errors → Immediate failure

## Performance Optimization

### Current
- Database indexing
- Query optimization
- Pagination

### Future
- Connection pooling
- Async LLM calls
- Batch processing
- Result caching

## Maintenance

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Cleanup Tasks
- Archive old jobs
- Prune validation history
- Monitor storage growth

## Development Workflow

1. Local development with SQLite/PostgreSQL
2. Git feature branches
3. Unit tests before commit
4. Integration tests in CI/CD
5. Code review
6. Staging deployment
7. Production deployment

## Future Roadmap

1. **Q1**: Celery integration for async processing
2. **Q2**: Enhanced validation with custom rules
3. **Q3**: Support for nested/complex schemas
4. **Q4**: ML-based confidence scoring
