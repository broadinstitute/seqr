from collections import defaultdict
from datetime import datetime
from django.db import models, transaction
from django.db.models.query import prefetch_related_objects
import logging

from panelapp.panelapp_utils import get_updated_panels, get_valid_panel_genes, update_locus_list_genes_bulk, panel_description
from reference_data.models import LoadableModel
from seqr.models import LocusList as SeqrLocusList, LocusListGene as SeqrLocusListGene
from seqr.views.utils.json_to_orm_utils import update_model_from_json

logger = logging.getLogger(__name__)


class PaLocusList(models.Model):

    """PanelApp extension of seqr.models.LocusList."""

    seqr_locus_list = models.OneToOneField(
        SeqrLocusList,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    source = models.CharField(max_length=2, choices=[(source, source) for source in ['AU', 'UK']])
    panel_app_id = models.IntegerField(null=False, blank=False)
    disease_group = models.TextField(null=True, blank=True)
    disease_sub_group = models.TextField(null=True, blank=True)
    status = models.TextField(null=True, blank=True)
    version = models.TextField(null=True, blank=True)
    version_created = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('source', 'panel_app_id')

        json_fields = ['source', 'panel_app_id']


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

    class Meta:
        """Fields included in JSON in API calls."""

        json_fields = ['confidence_level', 'mode_of_inheritance']


class PaLoader(LoadableModel):
    SOURCE = None
    URL = None

    class Meta:
        abstract = True

    @classmethod
    def get_current_version(cls, **kwargs):
        # Panel app has no global versioning, so update max once per day
        return datetime.now().strftime('%Y-%m-%d')

    @classmethod
    def panels_api_url(cls):
        return  f'{cls.URL}/api/v1/panels'

    @classmethod
    def load_records(cls, **kwargs):
        existing_list_versions = dict(PaLocusList.objects.filter(source=cls.SOURCE).values_list('panel_app_id', 'version'))
        panels_url = f'{cls.panels_api_url()}/?page=1'
        for record in get_updated_panels(panels_url, existing_list_versions):
            yield record

    @classmethod
    def update_record_models(cls, records, gene_ids_to_gene=None, **kwargs):
        updated_panels = {record.get('id'): record for record in records}
        existing_lists_by_id = {
            ll.panel_app_id: ll for ll in PaLocusList.objects.filter(source=cls.SOURCE, panel_app_id__in=updated_panels.keys())
        }
        new_panels = {
            panel_id: panel for panel_id, panel in updated_panels.items() if panel_id not in existing_lists_by_id
        }
        num_update = len(updated_panels) - len(new_panels)
        logger.info(f'Found {len(new_panels)} new and {num_update} existing panels to load')
        if not updated_panels:
            return 0

        if new_panels:
            existing_lists_by_id.update(cls._create_new_locus_lists(new_panels))
        prefetch_related_objects(list(existing_lists_by_id.values()), 'seqr_locus_list')

        genes_by_panel_id = defaultdict(list)
        updated_seqr_locuslists = []
        for panel_app_id, panel in updated_panels.items():
            try:
                logger.info(f'Importing panel id {panel_app_id}')
                with transaction.atomic():
                    pa_locus_list = existing_lists_by_id[panel_app_id]
                    seqr_locus_list = pa_locus_list.seqr_locus_list

                    update_model_from_json(pa_locus_list, {
                        'source': cls.SOURCE, **{field: panel.get(field) or None for field in [
                            'disease_group', 'disease_sub_group', 'status', 'version', 'version_created',
                        ]},
                    }, user=None)

                    panel_genes_by_id = get_valid_panel_genes(
                        panel_app_id, panel, cls.panels_api_url(), genes_by_panel_id, gene_ids_to_gene,
                    )
                    if panel_genes_by_id:
                        parsed_pa_genes = update_locus_list_genes_bulk(seqr_locus_list, panel_genes_by_id)
                        PaLocusListGene.objects.bulk_create(
                            [PaLocusListGene(**record) for record in parsed_pa_genes],
                            batch_size=10000,
                        )

                    seqr_locus_list.description = panel_description(panel_app_id, panel, cls.SOURCE)
                    updated_seqr_locuslists.append(seqr_locus_list)
            except Exception as e:
                logger.error('Error occurred when importing gene panel_app_id={}, error={}'.format(panel_app_id, e))

        SeqrLocusList.bulk_update_models(user=None, models=updated_seqr_locuslists, fields=['description'])
        return len(updated_seqr_locuslists)

    @classmethod
    def _create_new_locus_lists(cls, panels_by_id):
        created_locuslists = SeqrLocusList.bulk_create(user=None, new_models=[
            SeqrLocusList(name=panel['name'], is_public=True) for panel in panels_by_id.values()
        ])
        list_id_by_name = {ll.name: ll.id for ll in created_locuslists}

        created_pa_locuslists = PaLocusList.objects.bulk_create([
            PaLocusList(seqr_locus_list_id=list_id_by_name[panel['name']], panel_app_id=panel_app_id, source=cls.SOURCE)
            for panel_app_id, panel in panels_by_id.items()
        ])
        return {ll.panel_app_id: ll for ll in created_pa_locuslists}


class PanelAppAU(PaLoader):
    SOURCE = 'AU'
    URL = 'https://panelapp-aus.org'

    class Meta:
        abstract = True


class PanelAppUK(PaLoader):
    SOURCE = 'UK'
    URL = 'https://panelapp.genomicsengland.co.uk'

    class Meta:
        abstract = True
