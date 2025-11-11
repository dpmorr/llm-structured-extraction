"""Serializers for extraction service."""

from rest_framework import serializers
from .models import ExtractionJob, ExtractionResult, ValidationHistory


class ExtractionResultSerializer(serializers.ModelSerializer):
    """Serializer for extraction results."""

    class Meta:
        model = ExtractionResult
        fields = [
            'id',
            'field_name',
            'field_type',
            'value',
            'confidence',
            'source_text',
            'page_number',
            'is_valid',
            'validation_errors',
            'extraction_pass',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ValidationHistorySerializer(serializers.ModelSerializer):
    """Serializer for validation history."""

    class Meta:
        model = ValidationHistory
        fields = [
            'id',
            'action',
            'pass_number',
            'is_valid',
            'validation_errors',
            'repaired_fields',
            'repair_description',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ExtractionJobSerializer(serializers.ModelSerializer):
    """Serializer for extraction jobs."""

    results = ExtractionResultSerializer(many=True, read_only=True)
    validation_history = ValidationHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ExtractionJob
        fields = [
            'id',
            'document_id',
            'schema_name',
            'schema_description',
            'schema_definition',
            'status',
            'current_pass',
            'total_passes',
            'context',
            'llm_provider',
            'llm_model',
            'temperature',
            'total_fields',
            'extracted_fields',
            'confidence_score',
            'error_message',
            'retry_count',
            'max_retries',
            'prompt_tokens',
            'completion_tokens',
            'total_tokens',
            'project_id',
            'tags',
            'results',
            'validation_history',
            'created_at',
            'updated_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'current_pass',
            'total_fields',
            'extracted_fields',
            'confidence_score',
            'error_message',
            'retry_count',
            'prompt_tokens',
            'completion_tokens',
            'total_tokens',
            'results',
            'validation_history',
            'created_at',
            'updated_at',
            'completed_at',
        ]


class ExtractionJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating extraction jobs."""

    class Meta:
        model = ExtractionJob
        fields = [
            'document_id',
            'schema_name',
            'schema_description',
            'schema_definition',
            'context',
            'llm_provider',
            'llm_model',
            'temperature',
            'total_passes',
            'max_retries',
            'project_id',
            'tags',
        ]

    def validate_schema_definition(self, value):
        """Validate schema definition structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Schema definition must be a dictionary")

        if 'fields' not in value:
            raise serializers.ValidationError("Schema definition must contain 'fields' key")

        if not isinstance(value['fields'], list):
            raise serializers.ValidationError("'fields' must be a list")

        for field in value['fields']:
            if not isinstance(field, dict):
                raise serializers.ValidationError("Each field must be a dictionary")

            required_keys = ['name', 'description', 'type']
            for key in required_keys:
                if key not in field:
                    raise serializers.ValidationError(f"Field missing required key: {key}")

        return value

    def validate_total_passes(self, value):
        """Validate total passes."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Total passes must be between 1 and 5")
        return value

    def validate_temperature(self, value):
        """Validate temperature."""
        if value < 0 or value > 2:
            raise serializers.ValidationError("Temperature must be between 0 and 2")
        return value


class ExtractionRequestSerializer(serializers.Serializer):
    """Serializer for extraction requests (from shared schema)."""

    document_id = serializers.UUIDField()
    schema_name = serializers.CharField(max_length=255)
    schema_description = serializers.CharField()
    fields = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of field definitions"
    )
    context = serializers.CharField(required=False, allow_blank=True)
    llm_provider = serializers.CharField(required=False, default='openai')
    llm_model = serializers.CharField(required=False, default='gpt-4')
    temperature = serializers.FloatField(required=False, default=0.1)
    total_passes = serializers.IntField(required=False, default=2)
    project_id = serializers.UUIDField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )


class ExtractionResponseSerializer(serializers.Serializer):
    """Serializer for extraction responses (from shared schema)."""

    extraction_id = serializers.UUIDField()
    document_id = serializers.UUIDField()
    schema_name = serializers.CharField()
    status = serializers.CharField()
    results = serializers.ListField(child=serializers.DictField())
    confidence_score = serializers.FloatField(required=False, allow_null=True)
    metadata = serializers.DictField(required=False, default=dict)
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
