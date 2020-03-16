from django.core.management.base import BaseCommand

from seqr.models import Project, Family, VariantTag, VariantTagType
from seqr.views.apis.phenotips_api import _add_user_to_patient, _get_patient_data, _update_user_on_patient
from seqr.views.utils.phenotips_utils import phenotips_patient_exists, get_phenotips_uname_and_pwd_for_project


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--from-project', required=True)
        parser.add_argument('--to-project', required=True)
        parser.add_argument('family_ids', nargs='+')

    def handle(self, *args, **options):
        from_project = Project.objects.get(guid=options['from_project'])
        to_project = Project.objects.get(guid=options['to_project'])
        family_ids = options['family_ids']
        families = Family.objects.filter(project=from_project, family_id__in=family_ids)
        print('Found {} out of {} families. No match for: {}.'.format(len(families), len(set(family_ids)), set(family_ids) - set([f.family_id for f in families])))

        for f in families:
            print("==> Moving phenotips for {}".format(f))
            for seqr_individual in f.individual_set.all():

                if phenotips_patient_exists(seqr_individual):
                    # make sure phenotips_patient_id is up to date
                    data_json = _get_patient_data(
                        from_project,
                        seqr_individual,
                    )

                    seqr_individual.phenotips_patient_id = data_json["id"]
                    seqr_individual.save()

                    # update permissions
                    phenotips_readwrite_username, _ = get_phenotips_uname_and_pwd_for_project(to_project.phenotips_user_id, read_only=False)
                    _update_user_on_patient(seqr_individual.phenotips_patient_id, {
                        'transfer-to': 'on',
                        'owner': 'XWiki.' + str(phenotips_readwrite_username),
                    })

                    phenotips_readonly_username, _ = get_phenotips_uname_and_pwd_for_project(to_project.phenotips_user_id, read_only=True)
                    _add_user_to_patient(phenotips_readonly_username, seqr_individual.phenotips_patient_id, allow_edit=False)

        for variant_tag_type in VariantTagType.objects.filter(project=from_project):
            variant_tags = VariantTag.objects.filter(saved_variants__family__in=families, variant_tag_type=variant_tag_type)
            if variant_tags:
                print('Updating "{}" tags'.format(variant_tag_type.name))
                to_tag_type, created = VariantTagType.objects.get_or_create(
                    project=to_project, name=variant_tag_type.name
                )
                if created:
                    to_tag_type.category = variant_tag_type.category
                    to_tag_type.description = variant_tag_type.description
                    to_tag_type.color = variant_tag_type.color
                    to_tag_type.order = variant_tag_type.order
                    to_tag_type.save()
                variant_tags.update(variant_tag_type=to_tag_type)

        print("Updating families")
        families.update(project=to_project)

        print("Done.")
