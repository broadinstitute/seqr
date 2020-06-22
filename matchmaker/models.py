from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField

from seqr.models import ModelWithGUID, Individual
from settings import MME_DEFAULT_CONTACT_NAME, MME_DEFAULT_CONTACT_HREF


class MatchmakerSubmission(ModelWithGUID):

    SEX_LOOKUP = {Individual.SEX_MALE: 'MALE', Individual.SEX_FEMALE: 'FEMALE'}

    individual = models.OneToOneField(Individual, null=True, on_delete=models.SET_NULL)

    submission_id = models.CharField(max_length=255, db_index=True, unique=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    contact_name = models.TextField(default=MME_DEFAULT_CONTACT_NAME)
    contact_href = models.TextField(default=MME_DEFAULT_CONTACT_HREF)
    features = JSONField(null=True)
    genomic_features = JSONField(null=True)

    deleted_date = models.DateTimeField(null=True)
    deleted_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    def __unicode__(self):
        return '{}_submission_{}'.format(str(self.individual), self.id)

    def __str__(self):
        return '{}_submission_{}'.format(str(self.individual), self.id)

    def _compute_guid(self):
        return 'MS%07d_%s' % (self.id, str(self.individual))

    class Meta:
        json_fields = [
            'guid', 'created_date', 'last_modified_date', 'deleted_date'
        ]


class MatchmakerIncomingQuery(ModelWithGUID):
    institution = models.CharField(max_length=255)
    patient_id = models.CharField(max_length=255, null=True)

    def __unicode__(self):
        return '{}_{}_query'.format(self.patient_id or self.id, self.institution)

    def __str__(self):
        return '{}_{}_query'.format(self.patient_id or self.id, self.institution)

    def _compute_guid(self):
        return 'MIQ%07d_%s_%s' % (self.id, self.patient_id, self.institution.replace(' ', '_'))

    class Meta:
        json_fields = ['guid', 'created_date']


class MatchmakerResult(ModelWithGUID):
    submission = models.ForeignKey(MatchmakerSubmission, on_delete=models.PROTECT, null=True)
    originating_query = models.ForeignKey(MatchmakerIncomingQuery, on_delete=models.SET_NULL, null=True)
    result_data = JSONField()

    last_modified_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    we_contacted = models.BooleanField(default=False)
    host_contacted = models.BooleanField(default=False)
    deemed_irrelevant = models.BooleanField(default=False)
    flag_for_analysis = models.BooleanField(default=False)
    comments = models.TextField(null=True, blank=True)

    match_removed = models.BooleanField(default=False)

    def __unicode__(self):
        return '{}_{}_result'.format(self.id, str(self.submission))

    def __str__(self):
        return '{}_{}_result'.format(self.id, str(self.submission))

    def _compute_guid(self):
        return 'MR%07d_%s' % (self.id, str(self.submission))

    class Meta:
        json_fields = [
            'guid', 'comments', 'we_contacted', 'host_contacted', 'deemed_irrelevant', 'flag_for_analysis',
            'created_date', 'match_removed'
        ]


class MatchmakerContactNotes(ModelWithGUID):
    institution = models.CharField(max_length=200, db_index=True, unique=True)
    comments = models.TextField(blank=True)

    def __unicode__(self):
        return '{}_{}_contact'.format(self.id, self.institution)

    def __str__(self):
        return '{}_{}_contact'.format(self.id, self.institution)

    def _compute_guid(self):
        return 'MCN%07d_%s' % (self.id, self.institution.replace(' ', '_'))

    class Meta:
        json_fields = []
        internal_json_fields = ['institution', 'comments']
