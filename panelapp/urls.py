from django.conf import settings
from django.conf.urls import url
from social_core.utils import setting_name

from panelapp.views import import_panelapp_handler

extra = getattr(settings, setting_name('TRAILING_SLASH'), True) and '/' or ''

app_name = 'panelapp'

urlpatterns = [
    url(r'^api/locus_lists/import_panelapp$'.format(extra), import_panelapp_handler, name='import_panelapp_handler')
]
