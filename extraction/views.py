"""Views for extraction service."""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Q

from .models import ExtractionJob, ExtractionResult
from .serializers import (
    ExtractionJobSerializer,
    ExtractionJobCreateSerializer,
    ExtractionResultSerializer,
    ExtractionRequestSerializer,
    ExtractionResponseSerializer,
)
from .services import create_extraction_job, retry_extraction_job

logger = logging.getLogger(__name__)


class ExtractionJobViewSet(viewsets.ModelViewSet):
    """ViewSet for extraction jobs."""

    queryset = ExtractionJob.objects.all()
    serializer_class = ExtractionJobSerializer

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return ExtractionJobCreateSerializer
        return ExtractionJobSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = ExtractionJob.objects.all()

        # Filter by document_id
        document_id = self.request.query_params.get('document_id')
        if document_id:
            queryset = queryset.filter(document_id=document_id)

        # Filter by project_id
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by schema_name
        schema_name = self.request.query_params.get('schema_name')
        if schema_name:
            queryset = queryset.filter(schema_name__icontains=schema_name)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new extraction job."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract data
        data = serializer.validated_data

        try:
            # Create and start extraction job
            job = create_extraction_job(
                document_id=str(data['document_id']),
                schema_name=data['schema_name'],
                schema_description=data['schema_description'],
                fields=data['schema_definition']['fields'],
                context=data.get('context'),
                llm_provider=data.get('llm_provider'),
                llm_model=data.get('llm_model'),
                temperature=data.get('temperature'),
                total_passes=data.get('total_passes'),
                project_id=str(data['project_id']) if data.get('project_id') else None,
                tags=data.get('tags', []),
            )

            # Return job details
            response_serializer = ExtractionJobSerializer(job)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating extraction job: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed extraction job."""
        job = self.get_object()

        if job.status != 'failed':
            return Response(
                {'error': 'Only failed jobs can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            job = retry_extraction_job(str(job.id))
            serializer = self.get_serializer(job)
            return Response(serializer.data)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrying extraction job: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get extraction results for a job."""
        job = self.get_object()
        results = ExtractionResult.objects.filter(job=job).order_by('field_name')

        serializer = ExtractionResultSerializer(results, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def extract(self, request):
        """
        Main extraction endpoint compatible with shared schema.
        Accepts ExtractionRequest and returns ExtractionResponse.
        """
        request_serializer = ExtractionRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        data = request_serializer.validated_data

        try:
            # Create extraction job
            job = create_extraction_job(
                document_id=str(data['document_id']),
                schema_name=data['schema_name'],
                schema_description=data['schema_description'],
                fields=data['fields'],
                context=data.get('context'),
                llm_provider=data.get('llm_provider', 'openai'),
                llm_model=data.get('llm_model', 'gpt-4'),
                temperature=data.get('temperature', 0.1),
                total_passes=data.get('total_passes', 2),
                project_id=str(data['project_id']) if data.get('project_id') else None,
                tags=data.get('tags', []),
            )

            # Build response in shared schema format
            results = ExtractionResult.objects.filter(job=job)
            results_list = [
                {
                    'field_name': r.field_name,
                    'value': r.value,
                    'confidence': r.confidence,
                    'source_text': r.source_text,
                }
                for r in results
            ]

            response_data = {
                'extraction_id': str(job.id),
                'document_id': str(job.document_id),
                'schema_name': job.schema_name,
                'status': job.status,
                'results': results_list,
                'confidence_score': job.confidence_score,
                'metadata': {
                    'llm_provider': job.llm_provider,
                    'llm_model': job.llm_model,
                    'total_passes': job.total_passes,
                    'current_pass': job.current_pass,
                    'total_tokens': job.total_tokens,
                },
                'created_at': job.created_at,
                'completed_at': job.completed_at,
            }

            response_serializer = ExtractionResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error in extraction endpoint: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get extraction statistics."""
        queryset = self.get_queryset()

        stats = {
            'total_jobs': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'processing': queryset.filter(status='processing').count(),
            'completed': queryset.filter(status='completed').count(),
            'failed': queryset.filter(status='failed').count(),
            'average_confidence': queryset.filter(
                confidence_score__isnull=False
            ).aggregate(
                avg_confidence=models.Avg('confidence_score')
            )['avg_confidence'],
            'total_tokens_used': queryset.aggregate(
                total=models.Sum('total_tokens')
            )['total'],
        }

        return Response(stats)


class ExtractionResultViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for extraction results (read-only)."""

    queryset = ExtractionResult.objects.all()
    serializer_class = ExtractionResultSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = ExtractionResult.objects.all()

        # Filter by job_id
        job_id = self.request.query_params.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)

        # Filter by field_name
        field_name = self.request.query_params.get('field_name')
        if field_name:
            queryset = queryset.filter(field_name__icontains=field_name)

        # Filter by confidence threshold
        min_confidence = self.request.query_params.get('min_confidence')
        if min_confidence:
            queryset = queryset.filter(confidence__gte=float(min_confidence))

        # Filter by validity
        is_valid = self.request.query_params.get('is_valid')
        if is_valid is not None:
            queryset = queryset.filter(is_valid=is_valid.lower() == 'true')

        return queryset
