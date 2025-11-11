"""App configuration for extraction service."""

from django.apps import AppConfig


class ExtractionConfig(AppConfig):
    """Extraction app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'extraction'
    verbose_name = 'Extraction Service'

    def ready(self):
        """Import signals and perform app initialization."""
        pass
