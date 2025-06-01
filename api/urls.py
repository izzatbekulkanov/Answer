from django.urls import path
from .views import search_question, verify_pin, track_usage

urlpatterns = [
    path('v1/api/search-question', search_question, name='api_search_question'),
    path('v1/api/verify-pin/', verify_pin, name='verify_pin'),
    path('v1/api/track-usage/', track_usage, name='track_usage'),
]
