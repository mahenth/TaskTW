# student/views.py
from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Student
from .forms import StudentForm, CSVUploadForm

import csv
import json

class LoginView(View):
    def get(self, request):
        return render(request, 'student/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        return render(request, 'student/login.html', {'error': 'Invalid credentials'})\


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'student/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        search_query = self.request.GET.get('search', '')
        subject_filter = self.request.GET.get('subject', 'all')
        
        students_list = Student.objects.filter(user=self.request.user) # Filter by logged-in user
        
        if search_query:
            students_list = students_list.filter(
                Q(name__icontains=search_query) | Q(subject__icontains=search_query)
            )
        
        if subject_filter != 'all':
            students_list = students_list.filter(subject=subject_filter)

        all_subjects = Student.objects.filter(user=self.request.user).values_list('subject', flat=True).distinct()
        
        paginator = Paginator(students_list, 10)  # Show 10 students per page
        page_number = self.request.GET.get('page')
        try:
            students = paginator.page(page_number)
        except PageNotAnInteger:
            students = paginator.page(1)
        except EmptyPage:
            students = paginator.page(paginator.num_pages)

        context['students'] = students
        context['search_query'] = search_query
        context['subject_filter'] = subject_filter
        context['all_subjects'] = all_subjects
        return context


class AddStudentView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name')
        subject = request.POST.get('subject')
        marks_str = request.POST.get('marks')

        if not name or not subject or not marks_str:
            return JsonResponse({'success': False, 'message': 'All fields are required.'})

        try:
            marks = int(marks_str)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Marks must be a valid number.'})

        student, created = Student.objects.get_or_create(
            name=name,
            subject=subject,
            user=request.user,
            defaults={'marks': marks}
        )

        if not created:
            # If student exists, update their marks
            student.marks = marks # Overwrite existing marks as per initial behavior observed
            student.save()
        
        return JsonResponse({'success': True})


class EditStudentView(LoginRequiredMixin, View):
    def post(self, request, id):
        name = request.POST.get('name')
        subject = request.POST.get('subject')
        marks_str = request.POST.get('marks')

        try:
            marks = int(marks_str)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Marks must be a valid number.'})

        try:
            student = Student.objects.get(id=id, user=request.user)
            student.name = name
            student.subject = subject
            student.marks = marks
            student.save()
            return JsonResponse({'success': True})
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Student not found.'})


class DeleteStudentView(LoginRequiredMixin, View):
    def post(self, request, id):
        try:
            student = Student.objects.get(id=id, user=request.user)
            student.delete()
            return JsonResponse({'success': True})
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Student not found.'})


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'student/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        students = Student.objects.filter(user=self.request.user)
        subject_data = {}
        for student in students:
            subject_data.setdefault(student.subject, []).append(student.marks)

        summary = {
            subj: {
                'avg': sum(marks)/len(marks),
                'max': max(marks),
                'min': min(marks),
            } for subj, marks in subject_data.items()
        }

        return {'summary': summary}

class DeleteMultipleStudentsView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            ids_to_delete = data.get('ids', [])

            if not ids_to_delete:
                return JsonResponse({'success': False, 'message': 'No student IDs provided.'})

            # Ensure only students belonging to the logged-in user are deleted
            deleted_count, _ = Student.objects.filter(id__in=ids_to_delete, user=request.user).delete()
            
            if deleted_count > 0:
                return JsonResponse({'success': True, 'message': f'{deleted_count} students deleted successfully.'})
            else:
                return JsonResponse({'success': False, 'message': 'No matching students found or deleted.'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON in request body.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

class UploadCSVView(LoginRequiredMixin, FormView):
    form_class = CSVUploadForm
    template_name = 'student/upload.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        file = form.cleaned_data['file']
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)

        for row in reader:
            try:
                name = row['name']
                subject = row['subject']
                marks = int(row['marks']) # Attempt conversion here, for both existing and new

                student, created = Student.objects.get_or_create(
                    name=name,
                    subject=subject,
                    user=self.request.user,
                    defaults={'marks': marks}
                )
                if not created:
                    # If student already exists, update marks by adding the new marks
                    student.marks += marks
                    student.save()
                # If created, marks are already set by defaults={}
            except (ValueError, KeyError) as e:
                # Catch invalid marks (ValueError) or missing headers/keys (KeyError)
                print(f"Skipping row due to invalid data or missing key: {row} - Error: {e}")
                continue # Skip to the next row
            except Exception as e: # Catch any other unexpected errors during row processing
                print(f"An unexpected error occurred while processing row: {row} - Error: {e}")
                continue # Skip to the next row

        return super().form_valid(form)
