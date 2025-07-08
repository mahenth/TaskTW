# student/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Student
from io import StringIO
from django.core.files.uploadedfile import SimpleUploadedFile
import csv
import json


class StudentModelTest(TestCase):
    """Tests for the Student model."""
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_student_creation(self):
        student = Student.objects.create(name='John Doe', subject='Math', marks=90, user=self.user)
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.subject, 'Math')
        self.assertEqual(student.marks, 90)
        self.assertEqual(student.user, self.user)
        self.assertEqual(Student.objects.count(), 1)

    def test_student_str_representation(self):
        student = Student.objects.create(name='Jane Doe', subject='Physics', marks=85, user=self.user)
        self.assertEqual(str(student), 'Jane Doe - Physics')

class AuthenticationTests(TestCase):
    """Tests for user login and logout functionalities."""
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.login_url = reverse('login')
        self.home_url = reverse('home')
        self.logout_url = reverse('logout')

    def test_login_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student/login.html')

    def test_successful_login(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'password123'}, follow=True)
        self.assertRedirects(response, self.home_url)
        self.assertTrue(response.context['user'].is_authenticated)

    def test_failed_login(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student/login.html')
        self.assertContains(response, 'Invalid credentials')
        self.assertFalse(self.client.session.get('_auth_user_id')) # Ensure user is NOT logged in

    def test_logout(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.logout_url, follow=True)
        self.assertRedirects(response, self.login_url)
        self.assertFalse(self.client.session.get('_auth_user_id')) # Ensure user is logged out

class HomeViewTests(TestCase):
    """Tests for the Home page, including search and filter."""
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.home_url = reverse('home')

    def test_home_view_requires_login(self):
        response = self.client.get(self.home_url)
        self.assertRedirects(response, reverse('login') + '?next=' + self.home_url)

    def test_home_view_authenticated_access(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student/home.html')

    def test_home_view_context_data(self):
        self.client.login(username='testuser', password='password123')
        Student.objects.create(name='Student A', subject='Math', marks=80, user=self.user)
        Student.objects.create(name='Student B', subject='Physics', marks=70, user=self.user)
        
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        # Check the number of students on the current page returned by the paginator
        self.assertEqual(len(response.context['students']), 2) 

    def test_home_view_search_filter(self):
        self.client.login(username='testuser', password='password123')
        Student.objects.create(name='Alice Smith', subject='Math', marks=80, user=self.user)
        Student.objects.create(name='Bob Johnson', subject='Physics', marks=70, user=self.user)
        Student.objects.create(name='Alice Jones', subject='Chemistry', marks=90, user=self.user)

        # Test search by name
        response = self.client.get(self.home_url + '?search=Alice')
        self.assertEqual(response.status_code, 200)
        # Check students on the current paginated page
        self.assertEqual(len(response.context['students']), 2) # Alice Smith, Alice Jones
        self.assertContains(response, 'Alice Smith')
        self.assertContains(response, 'Alice Jones')

        # Test filter by subject
        response = self.client.get(self.home_url + '?subject=Math')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['students']), 1)
        self.assertContains(response, 'Alice Smith')
        self.assertNotContains(response, 'Bob Johnson')

        # Test combined search and filter (search for 'Alice' in 'Chemistry')
        response = self.client.get(self.home_url + '?search=Alice&subject=Chemistry')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['students']), 1)
        self.assertContains(response, 'Alice Jones')
        self.assertNotContains(response, 'Alice Smith')

class AddStudentViewTests(TestCase):
    """Tests for adding/updating student records."""
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.add_student_url = reverse('add_student')
        self.client.login(username='testuser', password='password123')

    def test_add_new_student(self):
        initial_student_count = Student.objects.filter(user=self.user).count()
        response = self.client.post(self.add_student_url, {
            'name': 'New Student',
            'subject': 'Biology',
            'marks': 75
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True})
        self.assertEqual(Student.objects.filter(user=self.user).count(), initial_student_count + 1)
        self.assertTrue(Student.objects.filter(name='New Student', subject='Biology', marks=75, user=self.user).exists())

    def test_update_existing_student_marks(self):
        # Create an existing student
        Student.objects.create(name='Existing Student', subject='Chemistry', marks=50, user=self.user)
        initial_student_count = Student.objects.filter(user=self.user).count()

        # Post new marks for the existing student (should overwrite 50 with 95)
        response = self.client.post(self.add_student_url, {
            'name': 'Existing Student',
            'subject': 'Chemistry',
            'marks': 95 
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True})
        
        # Verify that the marks are updated (replaced)
        updated_student = Student.objects.get(name='Existing Student', subject='Chemistry', user=self.user)
        self.assertEqual(updated_student.marks, 95)
        # Ensure no new student was created
        self.assertEqual(Student.objects.filter(user=self.user).count(), initial_student_count)

    def test_add_student_invalid_marks(self):
        initial_student_count = Student.objects.filter(user=self.user).count()
        response = self.client.post(self.add_student_url, {
            'name': 'Invalid Mark Student',
            'subject': 'Art',
            'marks': 'abc' # Invalid marks input
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': False, 'message': 'Marks must be a valid number.'})
        self.assertFalse(Student.objects.filter(name='Invalid Mark Student').exists())
        self.assertEqual(Student.objects.filter(user=self.user).count(), initial_student_count)

class DeleteStudentViewTests(TestCase):
    """Tests for deleting student records."""
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.delete_student_url_name = 'delete_student' # From urls.py
        self.client.login(username='testuser', password='password123')

    def test_delete_student_success(self):
        student = Student.objects.create(name='Student to Delete', subject='Math', marks=60, user=self.user)
        initial_count = Student.objects.filter(user=self.user).count()

        response = self.client.post(reverse(self.delete_student_url_name, args=[student.id]))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True})
        self.assertEqual(Student.objects.filter(user=self.user).count(), initial_count - 1)
        self.assertFalse(Student.objects.filter(id=student.id).exists())

    def test_delete_student_not_found(self):
        initial_count = Student.objects.filter(user=self.user).count()
        response = self.client.post(reverse(self.delete_student_url_name, args=[99999])) # Non-existent ID
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': False, 'message': 'Student not found.'})
        self.assertEqual(Student.objects.filter(user=self.user).count(), initial_count) # Count should remain same

    def test_delete_student_unauthenticated(self):
        student = Student.objects.create(name='Unauthorized Student', subject='Chem', marks=70, user=self.user)
        self.client.logout() # Log out the client to test unauthenticated access

        response = self.client.post(reverse(self.delete_student_url_name, args=[student.id]))
        # Should redirect to login page (LoginRequiredMixin default behavior)
        self.assertRedirects(response, reverse('login') + '?next=' + reverse(self.delete_student_url_name, args=[student.id]))
        self.assertTrue(Student.objects.filter(id=student.id).exists()) # Student should not be deleted

