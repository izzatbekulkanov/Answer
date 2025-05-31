from django.urls import path, include

from quiz_app import views
from quiz_app.views import QuestionListView

urlpatterns = [
    path('', views.index, name='index'),
    path('questions/', views.questions, name='questions'),
    path('hemis-upload/', views.hemis_upload, name='hemis_upload'),
    path('hemis-save/', views.hemis_save, name='hemis_save'),
    path('api/search', views.search_question, name='search_question'),
    path('api/questions/', QuestionListView.as_view(), name='question_list'),
    path('users/', views.users_list, name='users'),
    path('add-user/', views.add_user, name='add_user'),
    path('check-username/', views.check_username, name='check_username'),
    path('check-personal-code/', views.check_personal_code, name='check_personal_code'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    path('user/<int:user_id>/', views.user_detail, name='user_detail'),
    path('clean-duplicates/', views.clean_duplicates_view, name='clean_duplicates'),
    path('accounts/', include('django.contrib.auth.urls')),  # Django autentifikatsiyasi va logout
]
