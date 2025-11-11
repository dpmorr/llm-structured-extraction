"""Core extraction service using instructor + litellm."""

import logging
import json
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from pydantic import BaseModel, Field, create_model
import instructor
from litellm import completion
from django.conf import settings
from django.utils import timezone

from .models import ExtractionJob, ExtractionResult, ValidationHistory

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for structured data extraction using LLMs."""

    def __init__(self, job: ExtractionJob):
        """Initialize extraction service with a job."""
        self.job = job
        self.llm_provider = job.llm_provider
        self.llm_model = job.llm_model
        self.temperature = job.temperature

        # Configure LiteLLM based on provider
        self.model_name = self._get_model_name()

        # Set up API keys
        self._setup_credentials()

    def _get_model_name(self) -> str:
        """Get the full model name for litellm."""
        provider_prefixes = {
            'openai': '',  # OpenAI doesn't need prefix
            'anthropic': 'anthropic/',
            'bedrock': 'bedrock/',
        }
        prefix = provider_prefixes.get(self.llm_provider, '')
        return f"{prefix}{self.llm_model}"

    def _setup_credentials(self):
        """Set up credentials for the LLM provider."""
        # LiteLLM uses environment variables, but we can also pass them directly
        pass

    def _build_pydantic_model(self, schema_def: Dict[str, Any]) -> Type[BaseModel]:
        """Build a Pydantic model from schema definition."""
        fields = {}
        field_definitions = schema_def.get('fields', [])

        type_mapping = {
            'string': str,
            'number': float,
            'integer': int,
            'boolean': bool,
            'array': List[Any],
            'object': Dict[str, Any],
        }

        for field in field_definitions:
            field_name = field['name']
            field_type = field.get('type', 'string')
            description = field.get('description', '')
            required = field.get('required', False)
            example = field.get('example')

            # Get Python type
            python_type = type_mapping.get(field_type, str)

            # Make optional if not required
            if not required:
                python_type = Optional[python_type]

            # Create Field with description and example
            field_kwargs = {'description': description}
            if example is not None:
                field_kwargs['examples'] = [example]

            if required:
                fields[field_name] = (python_type, Field(**field_kwargs))
            else:
                fields[field_name] = (python_type, Field(default=None, **field_kwargs))

        # Create dynamic model
        model = create_model(
            schema_def.get('name', 'ExtractionModel'),
            **fields
        )

        return model

    def _get_document_text(self) -> str:
        """Retrieve document text for extraction."""
        # In a real implementation, this would fetch from the ingestion service
        # For now, we'll use a placeholder
        try:
            # Import here to avoid circular dependency
            import requests
            ingestion_url = settings.INGESTION_SERVICE_URL if hasattr(settings, 'INGESTION_SERVICE_URL') else 'http://localhost:8000'
            response = requests.get(f"{ingestion_url}/api/documents/{self.job.document_id}/")

            if response.status_code == 200:
                doc_data = response.json()
                return doc_data.get('raw_text', '')
            else:
                logger.error(f"Failed to fetch document: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Error fetching document text: {e}")
            # Return empty string so the job can still be processed
            return ""

    def _build_extraction_prompt(self, document_text: str, pydantic_model: Type[BaseModel]) -> str:
        """Build the extraction prompt."""
        schema_desc = self.job.schema_description
        context = self.job.context or ""

        prompt = f"""Extract structured information from the following document according to the schema.

Schema: {schema_desc}

Additional Context: {context}

Document Text:
{document_text}

Please extract all relevant information accurately. If a field cannot be determined from the document, leave it as null.
Provide your best estimate for confidence in the extraction.
"""
        return prompt

    def extract(self) -> bool:
        """Perform extraction with instructor."""
        try:
            self.job.status = 'processing'
            self.job.save()

            logger.info(f"Starting extraction for job {self.job.id}")

            # Get document text
            document_text = self._get_document_text()
            if not document_text:
                logger.warning(f"No document text for job {self.job.id}, using placeholder")
                document_text = "Document text not available."

            # Build Pydantic model from schema
            pydantic_model = self._build_pydantic_model(self.job.schema_definition)

            # Build extraction prompt
            prompt = self._build_extraction_prompt(document_text, pydantic_model)

            # Use instructor to patch the completion
            client = instructor.from_litellm(completion)

            logger.debug(f"Calling LLM with model: {self.model_name}")

            # Make the extraction call
            response = client.chat.completions.create(
                model=self.model_name,
                response_model=pydantic_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise data extraction assistant. Extract information accurately from documents."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=settings.LLM_MAX_TOKENS,
            )

            # Track usage (if available)
            if hasattr(response, '_raw_response'):
                raw = response._raw_response
                if hasattr(raw, 'usage'):
                    self.job.prompt_tokens = raw.usage.prompt_tokens or 0
                    self.job.completion_tokens = raw.usage.completion_tokens or 0
                    self.job.total_tokens = raw.usage.total_tokens or 0

            # Save results
            self._save_extraction_results(response)

            self.job.status = 'completed'
            self.job.completed_at = timezone.now()
            self.job.save()

            logger.info(f"Extraction completed for job {self.job.id}")
            return True

        except Exception as e:
            logger.error(f"Extraction failed for job {self.job.id}: {e}", exc_info=True)
            self.job.status = 'failed'
            self.job.error_message = str(e)
            self.job.retry_count += 1
            self.job.save()
            return False

    def _save_extraction_results(self, response: BaseModel):
        """Save extraction results to database."""
        # Get all fields from the response
        results_data = response.model_dump()
        schema_fields = {f['name']: f for f in self.job.schema_definition['fields']}

        total_confidence = 0.0
        field_count = 0

        for field_name, value in results_data.items():
            if field_name in schema_fields:
                field_def = schema_fields[field_name]

                # Calculate confidence (in real scenario, this would come from the model)
                # For now, we'll use a heuristic based on whether the value is null
                confidence = 0.9 if value is not None else 0.3

                ExtractionResult.objects.create(
                    job=self.job,
                    field_name=field_name,
                    field_type=field_def['type'],
                    value=value,
                    confidence=confidence,
                    extraction_pass=self.job.current_pass + 1,
                )

                total_confidence += confidence
                field_count += 1

        # Update job statistics
        self.job.total_fields = len(schema_fields)
        self.job.extracted_fields = field_count
        if field_count > 0:
            self.job.confidence_score = total_confidence / field_count
        self.job.current_pass += 1
        self.job.save()

    def validate_results(self) -> bool:
        """Validate extraction results."""
        try:
            self.job.status = 'validating'
            self.job.save()

            logger.info(f"Validating results for job {self.job.id}")

            results = ExtractionResult.objects.filter(
                job=self.job,
                extraction_pass=self.job.current_pass
            )

            validation_errors = []
            invalid_fields = []

            for result in results:
                # Check confidence threshold
                if result.confidence < 0.5:
                    validation_errors.append(
                        f"{result.field_name}: Low confidence ({result.confidence})"
                    )
                    invalid_fields.append(result.field_name)
                    result.is_valid = False
                    result.save()

                # Check for null values in required fields
                schema_fields = {f['name']: f for f in self.job.schema_definition['fields']}
                field_def = schema_fields.get(result.field_name)

                if field_def and field_def.get('required', False) and result.value is None:
                    validation_errors.append(
                        f"{result.field_name}: Required field is null"
                    )
                    invalid_fields.append(result.field_name)
                    result.is_valid = False
                    result.save()

            is_valid = len(validation_errors) == 0

            # Record validation history
            ValidationHistory.objects.create(
                job=self.job,
                action='validate',
                pass_number=self.job.current_pass,
                is_valid=is_valid,
                validation_errors=validation_errors if validation_errors else None,
            )

            logger.info(f"Validation {'passed' if is_valid else 'failed'} for job {self.job.id}")
            return is_valid

        except Exception as e:
            logger.error(f"Validation failed for job {self.job.id}: {e}", exc_info=True)
            return False

    def repair_results(self) -> bool:
        """Attempt to repair invalid results."""
        try:
            self.job.status = 'repairing'
            self.job.save()

            logger.info(f"Repairing results for job {self.job.id}")

            # Get invalid results
            invalid_results = ExtractionResult.objects.filter(
                job=self.job,
                extraction_pass=self.job.current_pass,
                is_valid=False
            )

            if not invalid_results:
                return True

            # Get document text
            document_text = self._get_document_text()

            # Build repair prompt focusing on invalid fields
            invalid_field_names = [r.field_name for r in invalid_results]
            schema_fields = [
                f for f in self.job.schema_definition['fields']
                if f['name'] in invalid_field_names
            ]

            # Create a subset model for repair
            repair_schema = {
                'name': f"{self.job.schema_name}_Repair",
                'fields': schema_fields
            }

            pydantic_model = self._build_pydantic_model(repair_schema)

            prompt = f"""Re-extract the following fields from the document. These fields had issues in the previous extraction.

Fields to re-extract: {', '.join(invalid_field_names)}

Document Text:
{document_text}

Please provide accurate values for these fields.
"""

            client = instructor.from_litellm(completion)

            response = client.chat.completions.create(
                model=self.model_name,
                response_model=pydantic_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise data extraction assistant. Re-extract specific fields accurately."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=settings.LLM_MAX_TOKENS,
            )

            # Update results
            repaired_fields = []
            results_data = response.model_dump()

            for field_name, value in results_data.items():
                result = invalid_results.filter(field_name=field_name).first()
                if result:
                    result.value = value
                    result.confidence = 0.85  # Higher confidence for repaired values
                    result.is_valid = True
                    result.save()
                    repaired_fields.append(field_name)

            # Record repair history
            ValidationHistory.objects.create(
                job=self.job,
                action='repair',
                pass_number=self.job.current_pass,
                is_valid=True,
                repaired_fields=repaired_fields,
                repair_description=f"Repaired {len(repaired_fields)} fields",
            )

            logger.info(f"Repaired {len(repaired_fields)} fields for job {self.job.id}")
            return True

        except Exception as e:
            logger.error(f"Repair failed for job {self.job.id}: {e}", exc_info=True)
            return False

    def run_multi_pass_extraction(self) -> bool:
        """Run multi-pass extraction with validation and repair."""
        try:
            max_passes = self.job.total_passes

            for pass_num in range(max_passes):
                logger.info(f"Starting pass {pass_num + 1}/{max_passes} for job {self.job.id}")

                # First pass: extract
                if pass_num == 0:
                    if not self.extract():
                        return False
                else:
                    # Subsequent passes: repair
                    if not self.repair_results():
                        return False

                # Validate results
                if self.validate_results():
                    logger.info(f"Validation passed on pass {pass_num + 1}, extraction complete")
                    self.job.status = 'completed'
                    self.job.completed_at = timezone.now()
                    self.job.save()
                    return True

                # If not the last pass, continue
                if pass_num < max_passes - 1:
                    logger.info(f"Validation failed on pass {pass_num + 1}, continuing to next pass")
                else:
                    logger.warning(f"Validation failed on final pass for job {self.job.id}")

            # Mark as completed even if validation didn't fully pass
            self.job.status = 'completed'
            self.job.completed_at = timezone.now()
            self.job.save()
            return True

        except Exception as e:
            logger.error(f"Multi-pass extraction failed for job {self.job.id}: {e}", exc_info=True)
            self.job.status = 'failed'
            self.job.error_message = str(e)
            self.job.save()
            return False


def create_extraction_job(
    document_id: str,
    schema_name: str,
    schema_description: str,
    fields: List[Dict[str, Any]],
    context: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    temperature: Optional[float] = None,
    total_passes: Optional[int] = None,
    project_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> ExtractionJob:
    """Create and initiate an extraction job."""

    # Build schema definition
    schema_definition = {
        'name': schema_name,
        'description': schema_description,
        'fields': fields,
    }

    # Create job
    job = ExtractionJob.objects.create(
        document_id=document_id,
        schema_name=schema_name,
        schema_description=schema_description,
        schema_definition=schema_definition,
        context=context,
        llm_provider=llm_provider or settings.LLM_PROVIDER,
        llm_model=llm_model or settings.LLM_MODEL,
        temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
        total_passes=total_passes or settings.EXTRACTION_VALIDATION_PASSES,
        max_retries=settings.EXTRACTION_MAX_RETRIES,
        project_id=project_id,
        tags=tags or [],
    )

    logger.info(f"Created extraction job {job.id}")

    # Start extraction
    service = ExtractionService(job)
    service.run_multi_pass_extraction()

    return job


def retry_extraction_job(job_id: str) -> ExtractionJob:
    """Retry a failed extraction job."""
    job = ExtractionJob.objects.get(id=job_id)

    if job.retry_count >= job.max_retries:
        raise ValueError(f"Job {job_id} has exceeded max retries")

    job.status = 'pending'
    job.error_message = None
    job.save()

    service = ExtractionService(job)
    service.run_multi_pass_extraction()

    return job
