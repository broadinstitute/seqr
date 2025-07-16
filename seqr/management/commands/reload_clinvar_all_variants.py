import gzip
import logging
import requests
import xml
import defusedxml.ElementTree as ET
from django.db import connections
from django.core.management.base import BaseCommand, CommandError
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL
from string import Template
from typing import Optional, Union

from clickhouse_backend import models
from clickhouse_search.models import ClinvarAllVariantsGRCh37SnvIndel, ClinvarAllVariantsSnvIndel, ClinvarAllVariantsMito
from reference_data.models import DataVersions
from seqr.utils.communication_utils import safe_post_to_slack

logger = logging.getLogger(__name__)

def replace_underscores_with_spaces(value: Union[str, list[str]]) -> Union[str, list[str]]:
    if isinstance(value, str):
        return value.replace('_', ' ')
    elif isinstance(value, list):
        return [s.replace('_', ' ') for s in value]
    raise TypeError("Expected str or list[str]")

def replace_spaces_with_underscores(value: Union[str, list[str], list[tuple[str, int]]]) -> Union[str, list[str]]:
    if isinstance(value, str):
        return value.replace(' ', '_')
    elif isinstance(value, list):
        if len(value) > 0 and isinstance(value[0], tuple):
            return [(t[0].replace(' ', '_'), t[1]) for t in value]
        return [s.replace(' ', '_') for s in value]
    raise TypeError("Expected str or list[str]")

BATCH_SIZE = 1000
CLINVAR_ASSERTIONS = replace_underscores_with_spaces(ClinvarAllVariantsSnvIndel.CLINVAR_ASSERTIONS)
CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY = replace_underscores_with_spaces(ClinvarAllVariantsSnvIndel.CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY)
CLINVAR_DEFAULT_PATHOGENICITY = replace_underscores_with_spaces(ClinvarAllVariantsSnvIndel.CLINVAR_DEFAULT_PATHOGENICITY)
CLINVAR_PATHOGENICITIES = replace_underscores_with_spaces(ClinvarAllVariantsSnvIndel.CLINVAR_PATHOGENICITIES)
CLINVAR_GOLD_STARS_LOOKUP = {
    'no classification for the single variant': 0,
    'no classification provided': 0,
    'no assertion criteria provided': 0,
    'no classifications from unflagged records': 0,
    'criteria provided, single submitter': 1,
    'criteria provided, conflicting classifications': 1,
    'criteria provided, multiple submitters, no conflicts': 2,
    'reviewed by expert panel': 3,
    'practice guideline': 4,
}
WEEKLY_XML_RELEASE = (
    'https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/ClinVarVCVRelease_00-latest.xml.gz'
)

def clinvar_run_sql(sql: str):
    with connections['clickhouse'].cursor() as cursor:
        for reference_genome, dataset_type in [
            ('GRCh37', 'SNV_INDEL'),
            ('GRCh38', 'SNV_INDEL'),
            ('GRCh38', 'MITO'),
        ]:
            cursor.execute(sql.substitute(reference_genome=reference_genome, dataset_type=dataset_type))


def parse_and_merge_classification_counts(text):
    #
    # Pathogenic(18); Likely pathogenic(9); Pathogenic, low penetrance(1); Established risk allele(1); Likely risk allele(1); Uncertain significance(1)
    #
    counts = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        label, count = part.rsplit("(", 1)
        label = label.strip()
        count = int(count.strip(")"))

        # Normalize away low penetrance
        label = label.replace(', low penetrance', '')

        counts[label] = counts.get(label, 0) + count
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)

def parse_allele_id(classified_record_node: xml.etree.ElementTree.Element) -> Optional[int]:
    allele_node = classified_record_node.find('SimpleAllele')
    if allele_node is None:
        return None
    allele_id_str = allele_node.attrib.get('AlleleID')
    if allele_id_str is None:
        return None
    try:
        allele_id = int(allele_id_str)
    except ValueError:
        return None
    return allele_id

def parse_positions(classified_record_node: xml.etree.ElementTree.Element) -> dict[dict]:
    positions = {}
    location_nodes = classified_record_node.findall('SimpleAllele/Location')
    if not location_nodes:
        # This does, occasionally happen.
        return positions
    for loc in location_nodes:
        for seq_loc in loc.findall('SequenceLocation'):
            if (
                seq_loc.get('referenceAlleleVCF')
                # Deletions will be filtered here.
                and seq_loc.get('alternateAlleleVCF')
                and seq_loc.get('positionVCF')
                and seq_loc.get('positionVCF').isdigit()
            ):
                positions[seq_loc.attrib['Assembly']] = {
                    'chrom': seq_loc.attrib['Chr'],
                    'pos': int(seq_loc.attrib['positionVCF']),
                    'ref': seq_loc.attrib['referenceAlleleVCF'],
                    'alt': seq_loc.attrib['alternateAlleleVCF'],
                }
    return positions

def parse_pathogenicity_and_assertions(classified_record_node: xml.etree.ElementTree.Element) -> [str, list[str]]:
    pathogenicity_node = classified_record_node.find(
        'Classifications/GermlineClassification/Description',
    )
    if pathogenicity_node is None:
        return CLINVAR_DEFAULT_PATHOGENICITY, []

    pathogenicity_string = pathogenicity_node.text.replace(
        '/Pathogenic, low penetrance/Established risk allele',
        '/Established risk allele; low penetrance',
    ).replace(
        '/Pathogenic, low penetrance',
        '; low penetrance',
    ).replace(
        ', low penetrance',
        '; low penetrance'
    )

    pathogenicity = pathogenicity_string.split(';')[0].strip()
    if pathogenicity in set(CLINVAR_PATHOGENICITIES):
        assertions = [a.strip() for a in pathogenicity_string.split(';')[1:]]
    else:
        pathogenicity = CLINVAR_DEFAULT_PATHOGENICITY
        assertions = [a.strip() for a in pathogenicity_string.split(';')]

    enumerated_assertions = set(CLINVAR_ASSERTIONS)
    for assertion in assertions:
        if assertion not in enumerated_assertions:
            raise CommandError(f'Found an un-enumerated clinvar assertion: {assertion}')

    return pathogenicity, assertions

def parse_conflicting_pathogenicities(
    classified_record_node: xml.etree.ElementTree.Element,
    pathogenicity: str,
) -> list[[str, int]]:
    if pathogenicity != CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY:
        return []
    conflicting_pathogenicities_node = classified_record_node.find(
        'Classifications/GermlineClassification/Explanation'
    )
    if conflicting_pathogenicities_node is None:
        return []
    conflicting_pathogenicities = parse_and_merge_classification_counts(
        conflicting_pathogenicities_node.text
    )
    enumerated_pathogenicities = set(CLINVAR_PATHOGENICITIES)
    for (pathogenicity, _) in conflicting_pathogenicities:
        if pathogenicity not in enumerated_pathogenicities:
            raise CommandError(f'Found an un-enumerated conflicting clinvar pathogenicity: {pathogenicity}')
    return conflicting_pathogenicities

def parse_gold_stars(classified_record_node: xml) -> Optional[int]:
    review_status_node = classified_record_node.find(
        'Classifications/GermlineClassification/ReviewStatus',
    )
    # NB: these are allowed for SomaticClassifcations.
    if review_status_node is None:
        return None
    if review_status_node.text not in CLINVAR_GOLD_STARS_LOOKUP:
        raise CommandError(f'Found unexpected review status {review_status_node.text}')
    return CLINVAR_GOLD_STARS_LOOKUP[review_status_node.text]

def parse_submitters_and_conditions(classified_record_node: xml) -> [list[str], list[str]]:
    submitters = sorted({
        s.attrib['SubmitterName']
        for s in classified_record_node.findall(
            'ClinicalAssertionList/ClinicalAssertion/ClinVarAccession',
        )
    })
    conditions = sorted({
        c.attrib['Name']
        for c in classified_record_node.findall('ClinicalAssertionList/TraitMappingList/TraitMapping/MedGen')
        if c.attrib['Name'] != 'not provided'
    })
    return submitters, conditions

def extract_variant_info(elem: xml.etree.ElementTree.Element, new_version: str) -> tuple[models.ClickhouseModel, models.ClickhouseModel, models.ClickhouseModel]:
    # Cannot use regular bool-falseyness here, as:
    # "An element with no child elements (even if it exists and has text) will be falsey."
    classified_record_node = elem.find('ClassifiedRecord')
    if classified_record_node is None:
        return None, None, None
    allele_id = parse_allele_id(classified_record_node)
    if allele_id is None: # Don't skip allele id of 0!
        return None, None, None
    positions = parse_positions(classified_record_node)
    if not positions:
        return None, None, None

    pathogenicity, assertions = parse_pathogenicity_and_assertions(classified_record_node)
    conflicting_pathogenicities = parse_conflicting_pathogenicities(classified_record_node, pathogenicity)
    gold_stars = parse_gold_stars(classified_record_node)
    submitters, conditions = parse_submitters_and_conditions(classified_record_node)
    props = {
        'version': new_version,
        'allele_id': allele_id,
        'pathogenicity': replace_spaces_with_underscores(pathogenicity),
        'assertions': replace_spaces_with_underscores(assertions),
        'conflicting_pathogenicities': replace_spaces_with_underscores(conflicting_pathogenicities),
        'gold_stars': gold_stars,
        'submitters': submitters,
        'conditions': conditions,
    }
    grch37 = positions.get('GRCh37')
    grch38 = positions.get('GRCh38')
    return (
        ClinvarAllVariantsGRCh37SnvIndel(
            variant_id=f"{grch37['chrom']}-{grch37['pos']}-{grch37['ref']}-{grch37['alt']}",
            **props,
        ) if grch37 and grch37['chrom'] != 'MT' else None,
        ClinvarAllVariantsSnvIndel(
            variant_id=f"{grch38['chrom']}-{grch38['pos']}-{grch38['ref']}-{grch38['alt']}",
            **props,
        ) if grch38 and grch38['chrom'] != 'MT'else None,
        ClinvarAllVariantsMito(
            variant_id=f"M-{grch38['pos']}-{grch38['ref']}-{grch38['alt']}",
            **props,
        ) if grch38 and grch38['chrom'] == 'MT' else None,
    )

class Command(BaseCommand):
    help = 'Reload all clinvar variants from weekly NCBI xml release'

    def handle(self, *args, **options):
        GRCh37SnvIndel_batch, SnvIndel_batch, Mito_batch = [], [], []
        new_version = None
        with requests.get(WEEKLY_XML_RELEASE, stream=True, timeout=10) as r:
            r.raise_for_status()
            for event, elem in ET.iterparse(gzip.GzipFile(fileobj=r.raw), events=('start', 'end',)):
                # Handle parsing the current date.
                if event == 'start' and elem.tag == 'ClinVarVariationRelease':
                    new_version = elem.attrib['ReleaseDate']
                    existing_version = (obj := DataVersions.objects.filter(data_model_name='Clinvar').first()) and obj.version
                    if new_version == existing_version:
                        logger.info(f'Clinvar ClickHouse tables already successfully updated to {new_version}, gracefully exiting.')
                        return
                    logger.info(f'Updating Clinvar ClickHouse tables to {new_version} from {existing_version}.')
                    clinvar_run_sql(
                        Template(f"ALTER TABLE `$reference_genome/$dataset_type/clinvar_all_variants` DROP PARTITION '{new_version}';")
                    )

                # Handle parsing variants
                if event == 'end' and elem.tag == 'VariationArchive' and new_version:
                    GRCh37SnvIndel, SnvIndel, Mito = extract_variant_info(elem, new_version)
                    for obj, batch, model in zip(
                        (GRCh37SnvIndel, SnvIndel, Mito),
                        (GRCh37SnvIndel_batch, SnvIndel_batch, Mito_batch),
                        (ClinvarAllVariantsGRCh37SnvIndel, ClinvarAllVariantsSnvIndel, ClinvarAllVariantsMito)
                    ):
                        if obj:
                            batch.append(obj)
                        if len(batch) == BATCH_SIZE:
                            model.objects.bulk_create(batch)
                            batch.clear()
                    elem.clear()

        for batch, model in zip(
            (GRCh37SnvIndel_batch, SnvIndel_batch, Mito_batch),
            (ClinvarAllVariantsGRCh37SnvIndel, ClinvarAllVariantsSnvIndel, ClinvarAllVariantsMito)
        ):
            if batch:
                model.objects.bulk_create(batch)

        # Delete previous version & refresh the view.
        if existing_version:
            clinvar_run_sql(Template(f"ALTER TABLE `$reference_genome/$dataset_type/clinvar_all_variants` DROP PARTITION '{existing_version}';"))
        clinvar_run_sql(Template('SYSTEM REFRESH VIEW `$reference_genome/$dataset_type/clinvar_all_variants_to_clinvar`;'))
        clinvar_run_sql(Template('SYSTEM WAIT VIEW `$reference_genome/$dataset_type/clinvar_all_variants_to_clinvar`;'))

        # Save the new version in Postgres
        DataVersions('Clinvar', new_version).save()
        slack_message = f'Successfully updated Clinvar ClickHouse tables to {new_version}.'
        safe_post_to_slack(SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, slack_message)
