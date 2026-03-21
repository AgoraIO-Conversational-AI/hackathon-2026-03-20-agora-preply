from django.db import models

from apps.core.models import TimeStampedModel


class Teacher(TimeStampedModel):
    preply_user_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    classtime_account_id = models.CharField(max_length=100, null=True, blank=True)
    classtime_token = models.TextField(blank=True, default="")
    classtime_token_expires_at = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()

    def __str__(self):
        return self.name


class Student(TimeStampedModel):
    preply_user_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    classtime_account_id = models.CharField(max_length=100, null=True, blank=True)
    classtime_token = models.TextField(blank=True, default="")
    classtime_token_expires_at = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()

    def __str__(self):
        return self.name
