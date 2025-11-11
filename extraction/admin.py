"""Admin configuration for extraction service."""

from django.contrib import admin
from django.utils.html import format_html
from .models import ExtractionJob, ExtractionResult, ValidationHistory


@admin.register(ExtractionJob)
class ExtractionJobAdmin(admin.ModelAdmin):
    """Admin interface for ExtractionJob."""

    list_display = [
        'id',
        'schema_name',
        'document_id',
        'status_badge',
        'confidence_display',
        'progress_display',
        'llm_model',
        'created_at',
    ]

    list_filter = [
        'status',
        'llm_provider',
        'created_at',
    ]

    search_fields = [
        'id',
        'document_id',
        'schema_name',
        'schema_description',
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'completed_at',
        'status',
        'current_pass',
        'extracted_fields',
        'confidence_score',
        'error_message',
        'prompt_tokens',
        'completion_tokens',
        'total_tokens',
    ]

    fieldsets = [
        ('Identification', {
            'fields': ['id', 'document_id', 'project_id']
        }),
        ('Schema', {
            'fields': ['schema_name', 'schema_description', 'schema_definition']
        }),
        ('Configuration', {
            'fields': ['llm_provider', 'llm_model', 'temperature', 'context']
        }),
        ('Status', {
            'fields': ['status', 'current_pass', 'total_passes', 'retry_count', 'max_retries']
        }),
        ('Results', {
            'fields': [
                'total_fields',
                'extracted_fields',
                'confidence_score',
                'error_message',
            ]
        }),
        ('Usage', {
            'fields': ['prompt_tokens', 'completion_tokens', 'total_tokens']
        }),
        ('Metadata', {
            'fields': ['tags', 'created_at', 'updated_at', 'completed_at']
        }),
    ]

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'pending': 'gray',
            'processing': 'blue',
            'validating': 'orange',
            'repairing': 'purple',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def confidence_display(self, obj):
        """Display confidence score with color coding."""
        if obj.confidence_score is None:
            return '-'

        if obj.confidence_score >= 0.8:
            color = 'green'
        elif obj.confidence_score >= 0.6:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1%}</span>',
            color,
            obj.confidence_score
        )
    confidence_display.short_description = 'Confidence'

    def progress_display(self, obj):
        """Display extraction progress."""
        if obj.total_fields == 0:
            return '-'

        percentage = (obj.extracted_fields / obj.total_fields) * 100
        return format_html(
            '{} / {} ({:.0f}%)',
            obj.extracted_fields,
            obj.total_fields,
            percentage
        )
    progress_display.short_description = 'Progress'


@admin.register(ExtractionResult)
class ExtractionResultAdmin(admin.ModelAdmin):
    """Admin interface for ExtractionResult."""

    list_display = [
        'id',
        'job',
        'field_name',
        'field_type',
        'value_preview',
        'confidence_display',
        'is_valid',
        'extraction_pass',
        'created_at',
    ]

    list_filter = [
        'field_type',
        'is_valid',
        'extraction_pass',
        'created_at',
    ]

    search_fields = [
        'id',
        'job__id',
        'field_name',
        'value',
        'source_text',
    ]

    readonly_fields = [
        'id',
        'job',
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

    fieldsets = [
        ('Job Information', {
            'fields': ['id', 'job', 'extraction_pass']
        }),
        ('Field Details', {
            'fields': ['field_name', 'field_type', 'value']
        }),
        ('Extraction Details', {
            'fields': ['confidence', 'source_text', 'page_number']
        }),
        ('Validation', {
            'fields': ['is_valid', 'validation_errors']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        }),
    ]

    def value_preview(self, obj):
        """Display truncated value."""
        value_str = str(obj.value)
        if len(value_str) > 50:
            return value_str[:50] + '...'
        return value_str
    value_preview.short_description = 'Value'

    def confidence_display(self, obj):
        """Display confidence score with color coding."""
        if obj.confidence >= 0.8:
            color = 'green'
        elif obj.confidence >= 0.6:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1%}</span>',
            color,
            obj.confidence
        )
    confidence_display.short_description = 'Confidence'


@admin.register(ValidationHistory)
class ValidationHistoryAdmin(admin.ModelAdmin):
    """Admin interface for ValidationHistory."""

    list_display = [
        'id',
        'job',
        'action',
        'pass_number',
        'is_valid_badge',
        'repaired_count',
        'created_at',
    ]

    list_filter = [
        'action',
        'is_valid',
        'created_at',
    ]

    search_fields = [
        'id',
        'job__id',
        'repair_description',
    ]

    readonly_fields = [
        'id',
        'job',
        'action',
        'pass_number',
        'is_valid',
        'validation_errors',
        'repaired_fields',
        'repair_description',
        'llm_response',
        'created_at',
    ]

    fieldsets = [
        ('Job Information', {
            'fields': ['id', 'job', 'action', 'pass_number']
        }),
        ('Validation', {
            'fields': ['is_valid', 'validation_errors']
        }),
        ('Repair', {
            'fields': ['repaired_fields', 'repair_description']
        }),
        ('LLM Response', {
            'fields': ['llm_response'],
            'classes': ['collapse']
        }),
        ('Timestamp', {
            'fields': ['created_at']
        }),
    ]

    def is_valid_badge(self, obj):
        """Display validation status as badge."""
        if obj.is_valid:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; '
                'border-radius: 3px;">VALID</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 3px 10px; '
                'border-radius: 3px;">INVALID</span>'
            )
    is_valid_badge.short_description = 'Valid'

    def repaired_count(self, obj):
        """Display count of repaired fields."""
        return len(obj.repaired_fields)
    repaired_count.short_description = 'Repaired Fields'
