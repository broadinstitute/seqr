from collections import defaultdict
import collections
import json
import logging
import re
import requests
import tempfile
import openpyxl as xl

from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import prefetch_related_objects
from django.utils import timezone

from seqr.utils.gene_utils import get_genes
from seqr.utils.xpos_utils import get_chrom_pos

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.saved_variant_api import variant_main_transcript, variant_details
from seqr.views.utils.json_utils import create_json_response, _to_title_case
from seqr.views.utils.orm_to_json_utils import _get_json_for_individuals, get_json_for_saved_variant
from reference_data.models import HPO_CATEGORY_NAMES
from seqr.models import Project, Family, VariantTag, VariantTagType, Sample, SavedVariant
from dateutil import relativedelta as rdelta
from django.db.models import Q, Prefetch
from django.shortcuts import render
from settings import LOGIN_URL, SEQR_ID_TO_MME_ID_MAP
from seqr.views.utils.orm_to_json_utils import _get_json_for_project

logger = logging.getLogger(__name__)


ZYGOSITY_MAP = {
    -1: 'no call',
    0: 'homozygous reference',
    1: 'heterozygous',
    2: 'homozygous alt',
}


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def anvil_export(request, project_guid=None):
    if project_guid:
        projects_by_guid = {project_guid: Project.objects.get(guid=project_guid)}
    else:
        projects_by_guid = {p.guid: p for p in Project.objects.filter(projectcategory__name__iexact='anvil')}

    families = _get_over_year_loaded_project_families(projects_by_guid.values())
    prefetch_related_objects(families, 'individual_set')

    saved_variants_by_family = _get_saved_variants_by_family(projects_by_guid.values(), request.user)

    individuals = set()
    for family in families:
        individuals.update(family.individual_set.all())
    rows = _get_json_for_individuals(list(individuals), project_guid=project_guid, add_family_id_field=True)

    for row in rows:
        row['Project ID'] = projects_by_guid[row['projectGuid']].name

        saved_variants = saved_variants_by_family[row['familyGuid']]
        row['numSavedVariants'] = len(saved_variants)
        if saved_variants:
            main_gene_ids = {variant['mainTranscript']['geneId'] for variant in saved_variants}
            if len(main_gene_ids) > 1:
                # This occurs in compound hets where some hits have a primary transcripts in different genes
                for gene_id in main_gene_ids:
                    if all(gene_id in variant['transcripts'] for variant in saved_variants):
                        row['geneId'] = gene_id
            else:
                row['geneId'] = main_gene_ids.pop()

            for i, variant in enumerate(saved_variants):
                genotype = variant['genotypes'].get(row['individualGuid'], {})
                variant_fields = {
                    'Zygosity': ZYGOSITY_MAP.get(genotype.get('numAlt')),
                    'Chrom': variant['chrom'],
                    'Pos': variant['pos'],
                    'Ref': variant['ref'],
                    'Alt': variant['alt'],
                    'hgvsc': variant['mainTranscript']['hgvsc'],
                    'hgvsp': variant['mainTranscript']['hgvsp'],
                    'Transcript': variant['mainTranscript']['transcriptId'],
                }
                row.update({'{} - {}'.format(k, i + 1): v for k, v in variant_fields.items()})

    genes_by_id = get_genes({row['geneId'] for row in rows if row.get('geneId')})
    for row in rows:
        if row.get('geneId') and genes_by_id.get(row['geneId']):
            row['Causal gene'] = genes_by_id[row['geneId']]['geneSymbol']

    #
    return create_json_response({'anvilRows': rows})


def _get_over_year_loaded_project_families(projects):
    max_loaded_date = datetime.now() - timedelta(days=365)
    loaded_samples = Sample.objects.filter(
        individual__family__project__in=projects,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_status=Sample.SAMPLE_STATUS_LOADED,
        loaded_date__isnull=False,
        loaded_date__lte=max_loaded_date,
    ).select_related('individual__family__project').order_by('loaded_date')
    
    return list({sample.individual.family for sample in loaded_samples})


def _get_saved_variants_by_family(projects, user):
    tag_type = VariantTagType.objects.get(name='Known gene for phenotype')

    project_saved_variants = SavedVariant.objects.select_related('family').filter(
        project__in=projects,
        varianttag__variant_tag_type=tag_type,
    )

    saved_variants_by_family = collections.defaultdict(list)
    for saved_variant in project_saved_variants:
        variant = get_json_for_saved_variant(saved_variant)
        variant_json = json.loads(saved_variant.saved_variant_json or '{}')
        variant.update(variant_details(variant_json, saved_variant.project, user, genotypes_by_individual_guid=True))

        saved_variants_by_family[saved_variant.family.guid].append(variant)

    return saved_variants_by_family


# TODO delete
def generate_rows(project, loaded_samples_by_project_family, saved_variants_by_project_family, errors, update_omim_and_gene_symbols=True):
    rows = []

    loaded_samples_by_family = loaded_samples_by_project_family[project.guid]
    saved_variants_by_family = saved_variants_by_project_family[project.guid]

    if not loaded_samples_by_family:
        errors.append("No data loaded for project: %s" % project)
        logger.info("No data loaded for project: %s" % project)
        return []

    if "external" in project.name or "reprocessed" in project.name:
        sequencing_approach = "REAN"
    else:
        sequencing_approach = loaded_samples_by_family.values()[0][-1].sample_type

    now = timezone.now()
    for family in project.families:
        samples = loaded_samples_by_family.get(family.guid)
        if not samples:
            errors.append("No data loaded for family: %s. Skipping..." % family)
            continue

        row = {
            "project_guid": project.guid,
            "family_guid": family.guid,
            "family_id": family.family_id,
            "collaborator": project.name,
            "sequencing_approach": sequencing_approach,
            "extras_pedigree_url": family.pedigree_image.url if family.pedigree_image else "",
            "coded_phenotype": family.coded_phenotype or "",
            "analysis_summary": (family.analysis_summary or '').strip('" \n'),
        }
        row.update(DEFAULT_ROW)

        t0 = samples[0].loaded_date
        t0_diff = rdelta.relativedelta(now, t0)
        t0_months_since_t0 = t0_diff.years * 12 + t0_diff.months
        row.update({
            "t0": t0,
            "t0_copy": t0,
            "months_since_t0": t0_months_since_t0,
        })
        if t0_months_since_t0 < 12:
            row['analysis_complete_status'] = "first_pass_in_progress"

        submitted_to_mme = SEQR_ID_TO_MME_ID_MAP.find_one({'project_id': project.deprecated_project_id, 'family_id': family.family_id})
        if submitted_to_mme:
            row["submitted_to_mme"] = "Y"

        phenotips_individual_data_records = [json.loads(i.phenotips_data) for i in family.individual_set.all() if i.phenotips_data]

        phenotips_individual_expected_inheritance_model = [
            inheritance_mode["label"] for phenotips_data in phenotips_individual_data_records for inheritance_mode in phenotips_data.get("global_mode_of_inheritance", [])
        ]
        if len(phenotips_individual_expected_inheritance_model) == 1:
            row["expected_inheritance_model"] = phenotips_individual_expected_inheritance_model.pop()

        phenotips_individual_mim_disorders = [phenotips_data.get("disorders", []) for phenotips_data in phenotips_individual_data_records]
        omim_number_initial = next((disorder["id"] for disorders in phenotips_individual_mim_disorders for disorder in disorders if "id" in disorder), '').replace("MIM:", "")
        if omim_number_initial:
            row.update({
                "omim_number_initial": omim_number_initial,
                "phenotype_class": "Known",
            })

        if family.post_discovery_omim_number:
            row["omim_number_post_discovery"] = family.post_discovery_omim_number

        phenotips_individual_features = [phenotips_data.get("features", []) for phenotips_data in phenotips_individual_data_records]
        category_not_set_on_some_features = False
        for features_list in phenotips_individual_features:
            for feature in features_list:
                if "category" not in feature:
                    category_not_set_on_some_features = True
                    continue

                if feature["observed"].lower() == "yes":
                    hpo_category_id = feature["category"]
                    hpo_category_name = HPO_CATEGORY_NAMES[hpo_category_id]
                    key = hpo_category_name.lower().replace(" ", "_").replace("/", "_")

                    row[key] = "Y"
                elif feature["observed"].lower() == "no":
                    continue
                else:
                    raise ValueError("Unexpected value for 'observed' in %s" % (feature,))

        if category_not_set_on_some_features:
            errors.append("HPO category field not set for some HPO terms in %s" % family)

        saved_variants = saved_variants_by_family.get(family.guid)
        if not saved_variants:
            rows.append(row)
            continue

        saved_variants_to_json = {}
        for variant in saved_variants:
            if not variant.saved_variant_json:
                errors.append("%s - variant annotation not found" % variant)
                rows.append(row)
                continue

            saved_variant_json = json.loads(variant.saved_variant_json)

            annotation = saved_variant_json.get('annotation') or {}
            gene_ids = annotation.get("coding_gene_ids", [])
            if not gene_ids:
                gene_ids = annotation.get("gene_ids", [])

            if not gene_ids:
                errors.append("%s - no gene ids" % variant)
                rows.append(row)
                continue

            saved_variant_json['geneIds'] = gene_ids

            saved_variants_to_json[variant] = saved_variant_json

        affected_sample_ids = set()
        unaffected_sample_ids = set()
        for sample in samples:
            if sample.individual.affected == "A":
                affected_sample_ids.add(sample.sample_id)
            elif sample.individual.affected == "N":
                unaffected_sample_ids.add(sample.sample_id)

        potential_compound_het_genes = defaultdict(set)
        for variant, saved_variant_json in saved_variants_to_json.items():
            inheritance_models = set()

            affected_indivs_with_hom_alt_variants = set()
            affected_indivs_with_het_variants = set()
            unaffected_indivs_with_hom_alt_variants = set()
            unaffected_indivs_with_het_variants = set()
            is_x_linked = False

            genotypes = saved_variant_json.get('genotypes')
            if genotypes:
                chrom, _ = get_chrom_pos(variant.xpos_start)
                is_x_linked = "X" in chrom
                for sample_id, genotype in genotypes.items():
                    if genotype["num_alt"] == 2 and sample_id in affected_sample_ids:
                        affected_indivs_with_hom_alt_variants.add(i.individual_id)
                    elif genotype["num_alt"] == 1 and sample_id in affected_sample_ids:
                        affected_indivs_with_het_variants.add(i.individual_id)
                    elif genotype["num_alt"] == 2 and sample_id in unaffected_sample_ids:
                        unaffected_indivs_with_hom_alt_variants.add(i.individual_id)
                    elif genotype["num_alt"] == 1 and sample_id in unaffected_sample_ids:
                        unaffected_indivs_with_het_variants.add(i.individual_id)

            # AR-homozygote, AR-comphet, AR, AD, de novo, X-linked, UPD, other, multiple
            if not unaffected_indivs_with_hom_alt_variants and affected_indivs_with_hom_alt_variants:
                if is_x_linked:
                    inheritance_models.add("X-linked")
                else:
                    inheritance_models.add("AR-homozygote")

            if not unaffected_indivs_with_hom_alt_variants and not unaffected_indivs_with_het_variants and affected_indivs_with_het_variants:
                if unaffected_sample_ids:
                    inheritance_models.add("de novo")
                else:
                    inheritance_models.add("AD")

            if not unaffected_indivs_with_hom_alt_variants and (len(
                    unaffected_sample_ids) < 2 or unaffected_indivs_with_het_variants) and affected_indivs_with_het_variants and not affected_indivs_with_hom_alt_variants:
                for gene_id in saved_variant_json['geneIds']:
                    potential_compound_het_genes[gene_id].add(variant)

            saved_variant_json['inheritance'] = inheritance_models

        gene_ids_to_saved_variants = defaultdict(set)
        gene_ids_to_variant_tag_names = defaultdict(set)
        gene_ids_to_inheritance = defaultdict(set)
        # Compound het variants are reported in the gene that they share
        for gene_id, variants in potential_compound_het_genes.items():
            if len(variants) > 1:
                gene_ids_to_inheritance[gene_id].add("AR-comphet")
                # Only include compound hets for one of the genes they are both in
                existing_gene_id = next((
                    existing_gene_id for existing_gene_id, existing_variants in gene_ids_to_saved_variants.items()
                    if existing_variants == variants), None)
                if existing_gene_id:
                    main_gene_ids = {
                        variant_main_transcript(saved_variants_to_json[variant])['geneId'] for variant in variants
                    }
                    if gene_id in main_gene_ids:
                        gene_ids_to_saved_variants[gene_id] = gene_ids_to_saved_variants[existing_gene_id]
                        del gene_ids_to_saved_variants[existing_gene_id]
                else:
                    for variant in variants:
                        saved_variants_to_json[variant]['inheritance'] = {"AR-comphet"}
                        gene_ids_to_variant_tag_names[gene_id].update(
                            {vt.variant_tag_type.name for vt in variant.discovery_tags})
                    gene_ids_to_saved_variants[gene_id].update(variants)

        # Non-compound het variants are reported in the main transcript gene
        for variant, saved_variant_json in saved_variants_to_json.items():
            if "AR-comphet" not in saved_variant_json['inheritance']:
                gene_id = variant_main_transcript(saved_variant_json)['geneId']
                gene_ids_to_saved_variants[gene_id].add(variant)
                gene_ids_to_variant_tag_names[gene_id].update({vt.variant_tag_type.name for vt in variant.discovery_tags})
                gene_ids_to_inheritance[gene_id].update(saved_variant_json['inheritance'])

        if len(gene_ids_to_saved_variants) > 1:
            row["gene_count"] = len(gene_ids_to_saved_variants)

        for gene_id, variants in gene_ids_to_saved_variants.items():
            # create a copy of the row dict
            row = dict(row)

            row["actual_inheritance_model"] = ", ".join(gene_ids_to_inheritance[gene_id])

            row["gene_id"] = gene_id

            variant_tag_names = gene_ids_to_variant_tag_names[gene_id]

            has_tier1 = any(name.startswith("Tier 1") for name in variant_tag_names)
            has_tier2 = any(name.startswith("Tier 2") for name in variant_tag_names)
            has_known_gene_for_phenotype = 'Known gene for phenotype' in variant_tag_names

            row.update({
                "solved": ("TIER 1 GENE" if (has_tier1 or has_known_gene_for_phenotype) else (
                    "TIER 2 GENE" if has_tier2 else "N")),
                "komp_early_release": "Y" if 'Share with KOMP' in variant_tag_names else "N",
            })

            if has_tier1 or has_tier2 or has_known_gene_for_phenotype:
                row.update({
                    "posted_publicly":  "",
                    "analysis_complete_status": "complete",
                    "novel_mendelian_gene":  "Y" if any("Novel gene" in name for name in variant_tag_names) else "N",
                })

            if any(tag in variant_tag_names for tag in [
                'Tier 1 - Phenotype expansion', 'Tier 1 - Novel mode of inheritance',  'Tier 2 - Phenotype expansion',
            ]):
                row["phenotype_class"] = "EXPAN"
            elif any(tag in variant_tag_names for tag in [
                'Tier 1 - Phenotype not delineated', 'Tier 2 - Phenotype not delineated'
            ]):
                row["phenotype_class"] = "UE"

            if not submitted_to_mme:
                if has_tier1 or has_tier2:
                    row["submitted_to_mme"] = "N" if t0_months_since_t0 > 7 else "TBD"
                elif has_known_gene_for_phenotype:
                    row["submitted_to_mme"] = "KPG"

            if has_tier1 or has_tier2:
                for functional_field in FUNCTIONAL_DATA_FIELD_MAP.values():
                    if functional_field == ADDITIONAL_KINDREDS_FIELD:
                        row[functional_field] = "1"
                    elif functional_field in METADATA_FUNCTIONAL_DATA_FIELDS:
                        row[functional_field] = "NA"
                    else:
                        row[functional_field] = "N"
            elif has_known_gene_for_phenotype:
                for functional_field in FUNCTIONAL_DATA_FIELD_MAP.values():
                    row[functional_field] = "KPG"

            variant_tag_list = []
            for variant in variants:
                variant_id = "-".join(map(str, list(get_chrom_pos(variant.xpos_start)) + [variant.ref, variant.alt]))
                variant_tag_list += [(variant_id, gene_id, vt.variant_tag_type.name.lower())
                                     for vt in variant.discovery_tags]

                for f in variant.variantfunctionaldata_set.all():
                    functional_field = FUNCTIONAL_DATA_FIELD_MAP[f.functional_data_tag]
                    if functional_field in METADATA_FUNCTIONAL_DATA_FIELDS:
                        value = f.metadata
                        if functional_field == ADDITIONAL_KINDREDS_FIELD:
                            value = str(int(value) + 1)
                        if row[functional_field] != 'NS':
                            value = '{} {}'.format(row[functional_field], value)
                    else:
                        value = 'Y'

                    row[functional_field] = value

            row["extras_variant_tag_list"] = variant_tag_list

            rows.append(row)

    if update_omim_and_gene_symbols:
        _update_gene_symbols(rows)
        _update_initial_omim_numbers(rows)

    return rows


def _update_gene_symbols(rows):
    genes_by_id = get_genes({row['gene_id'] for row in rows if row.get('gene_id')})
    for row in rows:
        if row.get('gene_id') and genes_by_id.get(row['gene_id']):
            row['gene_name'] = genes_by_id[row['gene_id']]['geneSymbol']

        row["extras_variant_tag_list"] = ["{variant_id}  {gene_symbol}  {tag}".format(
            variant_id=variant_id, gene_symbol=genes_by_id.get(gene_id, {}).get('geneSymbol'), tag=tag,
        ) for variant_id, gene_id, tag in row.get("extras_variant_tag_list", [])]


def _update_initial_omim_numbers(rows):
    omim_numbers = {row['omim_number_initial'] for row in rows if row['omim_number_initial']}
    omim_number_map = {}
    # OMIM API works for doing this as a single bulk request in theory but they detect us as a craweler and block us
    for omim_number_initial in omim_numbers:
        try:
            response = requests.get('https://www.omim.org/entry/' + omim_number_initial, headers={
                'Host': 'www.omim.org',
                'Connection': 'keep-alive',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
                'Upgrade-Insecure-Requests': '1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            })

            if not response.ok:
                raise ValueError("omim request failed: %s %s" % (response, response.reason))
            omim_page_html = response.content

            # <a href="/phenotypicSeries/PS613280" class="btn btn-info" role="button"> Phenotypic Series </a>
            match = re.search("/phenotypicSeries/([a-zA-Z0-9]+)", omim_page_html)
            if not match:
                logger.debug("No phenotypic series found for OMIM initial # %s" % omim_number_initial)
            else:
                phenotypic_series_id = match.group(1)
                logger.debug("Will replace OMIM initial # %s with phenotypic series %s" % (omim_number_initial, phenotypic_series_id))
                omim_number_map[omim_number_initial] = phenotypic_series_id
        except Exception as e:
            # don't change omim_number_initial
            logger.info(
                "Unable to look up phenotypic series for OMIM initial number: %s. %s" % (omim_number_initial, e))

    for row in rows:
        if omim_number_map.get(row['omim_number_initial']):
            row['omim_number_initial'] = omim_number_map[row['omim_number_initial']]
