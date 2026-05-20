from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .managers import CustomUserManager

class CustomUser(AbstractUser):
    """
    Custom user model for saving_manager_web.
    Using email as the primary identifier instead of username.
    """
    username = None
    email = models.EmailField(_('email address'), unique=True)
    full_name = models.CharField(max_length=50, default="")
    citizen_id = models.CharField(
        max_length=12,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{12}$',
                message='Citizen ID must contain exactly 12 digits.'
            )
        ]
    )
    address = models.CharField(max_length=100, default="")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
