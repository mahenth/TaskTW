# models.py
from django.db import models
from django.contrib.auth.models import User

class Student(models.Model):
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    marks = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True) # New field
    updated_at = models.DateTimeField(auto_now=True)   # New field

    def __str__(self):
        return f"{self.name} - {self.subject}"