from django.urls import path
from .views import (
    LoginView, LogoutView, HomeView,
    AddStudentView, EditStudentView, DeleteStudentView,
    UploadCSVView,
    DeleteMultipleStudentsView
)

urlpatterns = [
    path('', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('home/', HomeView.as_view(), name='home'),
    path('add/', AddStudentView.as_view(), name='add_student'),
    path('edit/<int:id>/', EditStudentView.as_view(), name='edit_student'),
    path('delete/<int:id>/', DeleteStudentView.as_view(), name='delete_student'),
    path('upload-csv/', UploadCSVView.as_view(), name='upload_csv'),
    path('delete-multiple/', DeleteMultipleStudentsView.as_view(), name='delete_multiple_students'), # New URL
]