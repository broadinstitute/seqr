from django.apps import AppConfig

class SeqrConfig(AppConfig):
    name = 'seqr'

    def ready(self):
        import seqr.signals  # noqa: F401

