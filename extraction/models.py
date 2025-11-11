"""Models for extraction service."""

from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class ExtractionJob(models.Model):
    """Extraction job tracking."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('validating', 'Validating'),
        ('repairing', 'Repairing'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Document reference
    document_id = models.UUIDField(db_index=True)

    # Schema definition
    schema_name = models.CharField(max_length=255)
    schema_description = models.TextField()
    schema_definition = models.JSONField()  # Store the ExtractionSchema

    # Status and processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_pass = models.IntegerField(default=0)
    total_passes = models.IntegerField(default=1)

    # Context and configuration
    context = models.TextField(null=True, blank=True)
    llm_provider = models.CharField(max_length=50, default='openai')
    llm_model = models.CharField(max_length=100, default='gpt-4')
    temperature = models.FloatField(default=0.1)

    # Results metadata
    total_fields = models.IntegerField(default=0)
    extracted_fields = models.IntegerField(default=0)
    confidence_score = models.FloatField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    # LLM usage
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    # Project association
    project_id = models.UUIDField(null=True, blank=True, db_index=True)
    tags = ArrayField(models.CharField(max_length=100), default=list, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'extraction_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['document_id', 'created_at']),
            models.Index(fields=['project_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.schema_name} - {self.document_id} ({self.status})"


class ExtractionResult(models.Model):
    """Individual field extraction result."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ExtractionJob, on_delete=models.CASCADE, related_name='results')

    # Field information
    field_name = models.CharField(max_length=255, db_index=True)
    field_type = models.CharField(max_length=50)  # string, number, boolean, date, array, object

    # Extracted value
    value = models.JSONField()  # Store any type of value
    confidence = models.FloatField()  # 0.0 to 1.0

    # Source information
    source_text = models.TextField(null=True, blank=True)  # Original text snippet
    page_number = models.IntegerField(null=True, blank=True)

    # Validation
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(null=True, blank=True)

    # Pass tracking (for multi-pass extraction)
    extraction_pass = models.IntegerField(default=1)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'extraction_results'
        ordering = ['job', 'field_name']
        indexes = [
            models.Index(fields=['job', 'field_name']),
            models.Index(fields=['field_name', 'created_at']),
        ]
        unique_together = [['job', 'field_name', 'extraction_pass']]

    def __str__(self):
        return f"{self.field_name}: {self.value} (confidence: {self.confidence})"


class ValidationHistory(models.Model):
    """Track validation and repair attempts."""

    ACTION_CHOICES = [
        ('validate', 'Validate'),
        ('repair', 'Repair'),
        ('retry', 'Retry'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ExtractionJob, on_delete=models.CASCADE, related_name='validation_history')

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    pass_number = models.IntegerField()

    # Validation results
    is_valid = models.BooleanField()
    validation_errors = models.JSONField(null=True, blank=True)

    # Repair information
    repaired_fields = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    repair_description = models.TextField(null=True, blank=True)

    # LLM response
    llm_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'validation_history'
        ordering = ['job', 'pass_number', 'created_at']
        indexes = [
            models.Index(fields=['job', 'pass_number']),
        ]

    def __str__(self):
        return f"{self.action} - Pass {self.pass_number} - {'Valid' if self.is_valid else 'Invalid'}"
