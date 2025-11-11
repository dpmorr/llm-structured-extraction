"""URL configuration for extraction app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExtractionJobViewSet, ExtractionResultViewSet

router = DefaultRouter()
router.register(r'jobs', ExtractionJobViewSet, basename='extraction-job')
router.register(r'results', ExtractionResultViewSet, basename='extraction-result')

urlpatterns = [
    path('', include(router.urls)),
    path('extractions/', include([
        path('', ExtractionJobViewSet.as_view({'post': 'extract'}), name='extract'),
    ])),
]
