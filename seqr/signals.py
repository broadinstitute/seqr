from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower


def validate_unique_email(sender, instance, raw, **kwargs):
    if raw or not instance.email:
        return
    if User.objects.annotate(email_lower=Lower('email')).filter(
        email_lower=instance.email.lower(),
    ).exclude(pk=instance.pk).exists():
        raise ValidationError('That email is already taken.')
