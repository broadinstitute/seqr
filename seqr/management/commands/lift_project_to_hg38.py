import logging
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.db.models import prefetch_related_objects
from django.db.models.query_utils import Q
from pyliftover.liftover import LiftOver

from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Project, SavedVariant, Individual
from seqr.views.apis.dataset_api import _update_variant_samples
from seqr.views.utils.dataset_utils import match_sample_ids_to_sample_records, validate_index_metadata, \
    get_elasticsearch_index_samples
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants
from seqr.views.utils.variant_utils import reset_cached_search_results
from seqr.utils.elasticsearch.utils import get_es_variants_for_variant_tuples, get_single_es_variant
from seqr.utils.xpos_utils import get_xpos

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('--project', required=True)
        parser.add_argument('--es-index', required=True)

    def handle(self, *args, **options):
        """transfer project"""
        project_arg = options['project']
        elasticsearch_index = options['es_index']

        project = Project.objects.get(Q(name=project_arg) | Q(guid=project_arg))
        logger.info('Updating project genome version for {}'.format(project.name))

        # Validate the provided index
        logger.info('Validating es index {}'.format(elasticsearch_index))
        sample_ids, index_metadata = get_elasticsearch_index_samples(elasticsearch_index)
        validate_index_metadata(index_metadata, project, elasticsearch_index, genome_version=GENOME_VERSION_GRCh38)
        sample_type = index_metadata['sampleType']

        matched_sample_id_to_sample_record = match_sample_ids_to_sample_records(
            project=project,
            user=None,
            sample_ids=sample_ids,
            sample_type=sample_type,
            elasticsearch_index=elasticsearch_index,
            sample_id_to_individual_id_mapping={},
        )

        unmatched_samples = set(sample_ids) - set(matched_sample_id_to_sample_record.keys())
        if len(unmatched_samples) > 0:
            raise CommandError('Matches not found for ES sample ids: {}.'.format(', '.join(unmatched_samples)))

        prefetch_related_objects(list(matched_sample_id_to_sample_record.values()), 'individual__family')
        included_families = {sample.individual.family for sample in matched_sample_id_to_sample_record.values()}
        missing_individuals = Individual.objects.filter(
            family__in=included_families,
            sample__is_active=True,
        ).exclude(sample__in=matched_sample_id_to_sample_record.values()).select_related('family')
        missing_family_individuals = defaultdict(list)
        for individual in missing_individuals:
            missing_family_individuals[individual.family].append(individual)

        if missing_family_individuals:
            raise CommandError(
                'The following families are included in the callset but are missing some family members: {}.'.format(
                    ', '.join(['{} ({})'.format(family.family_id, ', '.join([i.individual_id for i in missing_indivs]))
                               for family, missing_indivs in missing_family_individuals.items()])
                ))

        # Get expected saved variants
        saved_variant_models_by_guid = {v.guid: v for v in SavedVariant.objects.filter(family__project=project)}

        expected_families = {sv.family for sv in saved_variant_models_by_guid.values()}
        missing_families = expected_families - included_families
        if missing_families:
            raise CommandError(
                'The following families have saved variants but are missing from the callset: {}.'.format(
                    ', '.join([f.family_id for f in missing_families])
                ))

        # Lift-over saved variants
        _update_variant_samples(matched_sample_id_to_sample_record, None, elasticsearch_index)
        saved_variants = get_json_for_saved_variants(list(saved_variant_models_by_guid.values()), add_details=True)
        saved_variants_to_lift = [v for v in saved_variants if v['genomeVersion'] != GENOME_VERSION_GRCh38]

        num_already_lifted = len(saved_variants) - len(saved_variants_to_lift)
        if num_already_lifted:
            if input('Found {} saved variants already on Hg38. Continue with liftover (y/n)? '.format(num_already_lifted)) != 'y':
                raise CommandError('Error: found {} saved variants already on Hg38'.format(num_already_lifted))
        logger.info('Lifting over {} variants (skipping {} that are already lifted)'.format(
            len(saved_variants_to_lift), num_already_lifted))

        liftover_to_38 = LiftOver('hg19', 'hg38')
        hg37_to_hg38_xpos = {}
        lift_failed = {}
        for v in saved_variants_to_lift:
            if not (hg37_to_hg38_xpos.get(v['xpos']) or v['xpos'] in lift_failed):
                hg38_coord = liftover_to_38.convert_coordinate('chr{}'.format(v['chrom'].lstrip('chr')), int(v['pos']))
                if hg38_coord and hg38_coord[0]:
                    hg37_to_hg38_xpos[v['xpos']] = get_xpos(hg38_coord[0][0], hg38_coord[0][1])
                else:
                    lift_failed[v['xpos']] = v

        if lift_failed:
            if input(
                'Unable to lift over the following {} coordinates. Continue with update (y/n)?: {} '.format(
                    len(lift_failed), ', '.join([
                        '{}:{}-{}-{} ({})'.format(v['chrom'], v['pos'], v['ref'], v['alt'], ', '.join(v['familyGuids']))
                        for v in lift_failed.values()]))) != 'y':
                raise CommandError('Error: unable to lift over {} variants'.format(len(lift_failed)))

        saved_variants_map = defaultdict(list)
        for v in saved_variants_to_lift:
            if hg37_to_hg38_xpos.get(v['xpos']):
                variant_model = saved_variant_models_by_guid[v['variantGuid']]
                saved_variants_map[(hg37_to_hg38_xpos[v['xpos']], v['ref'], v['alt'])].append(variant_model)

        es_variants = get_es_variants_for_variant_tuples(expected_families, list(saved_variants_map.keys()))

        missing_variants = set(saved_variants_map.keys()) - {(v['xpos'], v['ref'], v['alt']) for v in es_variants}
        if missing_variants:
            missing_variant_strings = []
            for xpos, ref, alt in missing_variants:
                var_id = '{}-{}-{}'.format(xpos, ref, alt)
                for v in saved_variants_map[(xpos, ref, alt)]:
                    tags = v.varianttag_set.all()
                    notes = v.variantnote_set.all()
                    missing_variant_strings.append('{var_id} {family_id}: {tags} ({guid})'.format(
                        var_id=var_id, family_id=v.family.family_id, guid=v.guid,
                        tags=', '.join([tag.variant_tag_type.name for tag in tags])if tags else 'No Tags; {}'.format(
                            '; '.join([note.note for note in notes]))
                    ))
            if input('Unable to find the following {} variants in the index. Continue with update (y/n)?:\n{}\n'.format(
                    len(missing_variants), '\n'.join(missing_variant_strings))) != 'y':
                raise CommandError('Error: unable to find {} lifted-over variants'.format(len(missing_variants)))

        logger.info('Successfully lifted over {} variants'.format(len(es_variants)))

        #  Update saved variants
        missing_family_count = 0
        for var in es_variants:
            saved_variant_models = saved_variants_map[(var['xpos'], var['ref'], var['alt'])]
            missing_saved_variants = [v for v in saved_variant_models if v.family.guid not in var['familyGuids']]
            if missing_saved_variants:
                variant_id = '{}-{}-{}-{}'.format(var['chrom'], var['pos'], var['ref'], var['alt'])
                if input(('Variant {} (hg37: {}) not find for expected families {}. Continue with update (y/n)? '.format(
                    variant_id, missing_saved_variants[0].xpos,
                    ', '.join(['{} ({})'.format(v.family.guid, v.guid) for v in missing_saved_variants]))
                )) == 'y':
                    var = get_single_es_variant([v.family for v in saved_variant_models], variant_id, return_all_queried_families=True)
                    missing_family_count += len(missing_saved_variants)
                else:
                    raise CommandError('Error: unable to find family data for lifted over variant')
            for saved_variant in saved_variant_models:
                saved_variant.xpos_start = var['xpos']
                saved_variant.saved_variant_json = var
                saved_variant.save()

        logger.info('Successfully updated {} variants'.format(len(es_variants)))

        # Update project and sample data
        update_model_from_json(project, {'genome_version': GENOME_VERSION_GRCh38}, None)

        reset_cached_search_results(project)

        logger.info('---Done---')
        logger.info('Succesfully lifted over {} variants. Skipped {} failed variants. Family data not updated for {} variants'.format(
            len(es_variants), len(missing_variants) + len(lift_failed), missing_family_count))
