from django.db import models
from django.db.models import JSONField

from seqr.models import LocusList as SeqrLocusList, LocusListGene as SeqrLocusListGene


class PaLocusList(models.Model):
    """PanelApp extension of seqr.models.LocusList."""

    seqr_locus_list = models.OneToOneField(
        SeqrLocusList,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    panel_app_id = models.IntegerField(null=False, blank=False, unique=True)
    disease_group = models.TextField(null=True, blank=True)
    disease_sub_group = models.TextField(null=True, blank=True)
    status = models.TextField(null=True, blank=True)
    version = models.TextField(null=True, blank=True)
    version_created = models.DateTimeField(null=True, blank=True)
    raw_data = JSONField(default=dict)

    class Meta:
        json_fields = ['panel_app_id', 'disease_group', 'disease_sub_group', 'status', 'version', 'version_created',
                       'raw_data']


class PaLocusListGene(models.Model):
    """PanelApp extension of seqr.models.LocusListGene."""

    CONFIDENCE_LEVEL_CHOICES = [
        ('1', 'RED'),
        ('2', 'AMBER'),
        ('3', 'GREEN'),
        ('4', 'GREEN'),
    ]

    seqr_locus_list_gene = models.OneToOneField(
        SeqrLocusListGene,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    confidence_level = models.CharField(max_length=1, choices=CONFIDENCE_LEVEL_CHOICES, null=False)
    biotype = models.TextField(null=True, blank=True)
    penetrance = models.TextField(null=True, blank=True)
    mode_of_pathogenicity = models.TextField(null=True, blank=True)
    mode_of_inheritance = models.TextField(null=True, blank=True)
    raw_data = JSONField(default=dict)

    class Meta:
        json_fields = ['confidence_level', 'biotype', 'penetrance', 'mode_of_pathogenicity', 'raw_data']
