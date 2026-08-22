from django.apps import AppConfig

class SeqrConfig(AppConfig):
    name = 'seqr'

    def ready(self):
        from django.contrib.auth.models import User
        from django.db.models.signals import pre_save
        from seqr.signals import validate_unique_email
        pre_save.connect(
            validate_unique_email, sender=User, dispatch_uid='seqr.validate_unique_email',
        )

