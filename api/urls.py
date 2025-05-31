from django.urls import path
from .views import search_question, verify_pin, track_usage

urlpatterns = [
    path('api/search/question', search_question, name='api_search_question'),
    path('api/verify-pin/', verify_pin, name='verify_pin'),
    path('api/track-usage/', track_usage, name='track_usage'),
]
