import gzip
from django.db import models
from xbrowse.parsers import vcf_stuff


STORAGE_MODES = (
    ('local', 'Local'),
    ('network', 'Network')
)

class BAMFile(models.Model):

    indiv_id = models.CharField(max_length=100)
    storage_mode = models.CharField(choices=STORAGE_MODES, max_length=20)
    file_path = models.TextField()
    network_url = models.TextField()

    def __unicode__(self):
        if self.storage_mode == 'network':
            return self.network_url
        else:
            return self.file_path

    def get_url(self):
        if self.storage_mode == 'network':
            return self.network_url
        else:
            return ''


class XHMMFile(models.Model):

    file_path = models.CharField(max_length=500, default="", blank=True)

    def __unicode__(self):
        return self.file_path

    def path(self):
        return self.file_path

    def file_handle(self):
        if self.file_path.endswith('.gz'):
            return gzip.open(self.file_path)
        else:
            return open(self.file_path)

    def sample_id_list(self):
        return vcf_stuff.get_ids_from_vcf_path(self.path())