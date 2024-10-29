from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField

from seqr.models import ModelWithGUID, Individual
from settings import MME_DEFAULT_CONTACT_NAME, MME_DEFAULT_CONTACT_HREF


class MatchmakerSubmission(ModelWithGUID):

    SEX_LOOKUP = {
        **{sex: 'MALE' for sex in Individual.MALE_SEXES},
        **{sex: 'FEMALE' for sex in Individual.FEMALE_SEXES},
    }

    individual = models.OneToOneField(Individual, on_delete=models.PROTECT)

    submission_id = models.CharField(max_length=255, db_index=True, unique=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    contact_name = models.TextField(default=MME_DEFAULT_CONTACT_NAME)
    contact_href = models.TextField(default=MME_DEFAULT_CONTACT_HREF)
    features = JSONField(null=True)

    deleted_date = models.DateTimeField(null=True)
    deleted_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    def __unicode__(self):
        return '{}_submission_{}'.format(str(self.individual), self.id)

    GUID_PREFIX = 'MS'

    class Meta:
        json_fields = [
            'guid', 'created_date', 'last_modified_date', 'deleted_date'
        ]


class MatchmakerSubmissionGenes(models.Model):
    matchmaker_submission = models.ForeignKey(MatchmakerSubmission, on_delete=models.CASCADE)
    saved_variant = models.ForeignKey('seqr.SavedVariant', on_delete=models.PROTECT)
    gene_id = models.CharField(max_length=20)  # ensembl ID


class MatchmakerIncomingQuery(ModelWithGUID):
    institution = models.CharField(max_length=255)
    patient_id = models.CharField(max_length=255, null=True)

    def __unicode__(self):
        return '{}_{}_query'.format(self.patient_id or self.id, self.institution)

    GUID_PREFIX = 'MIQ'

    class Meta:
        json_fields = ['guid', 'created_date']


class MatchmakerResult(ModelWithGUID):
    submission = models.ForeignKey(MatchmakerSubmission, on_delete=models.PROTECT, null=True)
    originating_submission = models.ForeignKey(MatchmakerSubmission, on_delete=models.PROTECT, null=True, related_name='origin_results')
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

    GUID_PREFIX = 'MR'

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

    GUID_PREFIX = 'MCN'

    class Meta:
        json_fields = []
        internal_json_fields = ['institution', 'comments']
