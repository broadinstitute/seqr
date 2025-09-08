import gzip
import requests
import xml
import defusedxml.ElementTree as ET
from django.db import connections
from django.core.management.base import CommandError
from collections import defaultdict
import re
from string import Template
from typing import Optional, Union

from clickhouse_backend import models
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37


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

CLINVAR_BATCH_SIZE = 1000
CLINVAR_ASSERTIONS = [
    'Affects',
    'association',
    'association_not_found',
    'confers_sensitivity',
    'drug_response',
    'low_penetrance',
    'not_provided',
    'other',
    'protective',
    'risk_factor',
    'no_classification_for_the_single_variant',
    'no_classifications_from_unflagged_records',
]
CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY = 'Conflicting_classifications_of_pathogenicity'
CLINVAR_DEFAULT_PATHOGENICITY = 'No_pathogenic_assertion'
CLINVAR_PATHOGENICITIES = [
    'Pathogenic',
    'Pathogenic/Likely_pathogenic',
    'Pathogenic/Likely_pathogenic/Established_risk_allele',
    'Pathogenic/Likely_pathogenic/Likely_risk_allele',
    'Pathogenic/Likely_risk_allele',
    'Likely_pathogenic',
    'Likely_pathogenic/Likely_risk_allele',
    'Established_risk_allele',
    'Likely_risk_allele',
    CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY,
    'Uncertain_risk_allele',
    'Uncertain_significance/Uncertain_risk_allele',
    'Uncertain_significance',
    CLINVAR_DEFAULT_PATHOGENICITY,
    'Likely_benign',
    'Benign/Likely_benign',
    'Benign',
]
CLINVAR_XML_ASSERTIONS = replace_underscores_with_spaces(CLINVAR_ASSERTIONS)
CLINVAR_XML_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY = replace_underscores_with_spaces(CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY)
CLINVAR_CONFLICTING_DATA_FROM_SUBMITTERS = 'conflicting data from submitters'
CLINVAR_XML_DEFAULT_PATHOGENICITY = replace_underscores_with_spaces(CLINVAR_DEFAULT_PATHOGENICITY)
CLINVAR_XML_PATHOGENICITIES = replace_underscores_with_spaces(CLINVAR_PATHOGENICITIES)
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
    with connections['clickhouse_write'].cursor() as cursor:
        for reference_genome, dataset_type in [
            ('GRCh37', 'SNV_INDEL'),
            ('GRCh38', 'SNV_INDEL'),
            ('GRCh38', 'MITO'),
        ]:
            cursor.execute(Template(sql).substitute(reference_genome=reference_genome, dataset_type=dataset_type))


def parse_and_merge_classification_counts(text: str) -> list[tuple[str, int]]:
    #
    # Example texts:
    # 'Pathogenic(18); Likely pathogenic(9); Pathogenic, low penetrance(1); Established risk allele(1); Likely risk allele(1); Uncertain significance(1)'
    # 'Uncertain significance(1), Likely benign (1)'
    counts = defaultdict(int)
    for label, count in re.findall(r'([\w\s,]+?)\s?\((\d+)\)[;,]?\s?', text):
        label = label.strip().replace(', low penetrance', '')
        counts[label] += int(count)
    if not counts:
        raise CommandError(f'Failed to correctly parse conflicting pathogenicity counts: {text}')
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)

def parse_allele_id(classified_record_node: xml.etree.ElementTree.Element) -> Optional[int]:
    allele_id_str = (allele_node := classified_record_node.find('SimpleAllele')) is not None and allele_node.attrib.get('AlleleID')
    if allele_id_str is None:
        return None
    return int(allele_id_str)

def parse_positions(classified_record_node: xml.etree.ElementTree.Element) -> dict[dict]:
    positions = {}
    location_nodes = classified_record_node.findall('SimpleAllele/Location')
    for loc in location_nodes:
        for seq_loc in loc.findall('SequenceLocation'):
            if (
                seq_loc.get('referenceAlleleVCF')
                # Deletions will be filtered here.
                and seq_loc.get('alternateAlleleVCF')
                and seq_loc.get('positionVCF')
                and seq_loc.get('positionVCF').isdigit()
                and seq_loc.get('referenceAlleleVCF') != seq_loc.get('alternateAlleleVCF')
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
        return CLINVAR_XML_DEFAULT_PATHOGENICITY, []

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

    if pathogenicity in set(CLINVAR_XML_PATHOGENICITIES) or pathogenicity == CLINVAR_CONFLICTING_DATA_FROM_SUBMITTERS:
        assertions = [a.strip() for a in pathogenicity_string.split(';')[1:]]
    else:
        pathogenicity = CLINVAR_XML_DEFAULT_PATHOGENICITY
        assertions = [a.strip() for a in pathogenicity_string.split(';')]

    enumerated_assertions = set(CLINVAR_XML_ASSERTIONS)
    for assertion in assertions:
        if assertion not in enumerated_assertions:
            raise CommandError(f'Found an un-enumerated clinvar assertion: {assertion}')

    return pathogenicity, assertions

def parse_conflicting_pathogenicities(
    classified_record_node: xml.etree.ElementTree.Element,
    pathogenicity: str,
) -> list[[str, int]]:
    if pathogenicity == CLINVAR_XML_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY:
        conflicting_pathogenicities_node = classified_record_node.find(
            'Classifications/GermlineClassification/Explanation'
        )
    elif pathogenicity == CLINVAR_CONFLICTING_DATA_FROM_SUBMITTERS:
        conflicting_pathogenicities_node = classified_record_node.find(
            'ClinicalAssertionList/ClinicalAssertion/Classification/Comment'
        )
    else:
        return []
    if conflicting_pathogenicities_node is None:
        raise CommandError('Failed to find the conflicting pathogenicities node')
    conflicting_pathogenicities = parse_and_merge_classification_counts(
        conflicting_pathogenicities_node.text
    )
    enumerated_pathogenicities = set(CLINVAR_XML_PATHOGENICITIES)
    for (pathogenicity, _) in conflicting_pathogenicities:
        if pathogenicity not in enumerated_pathogenicities:
            raise CommandError(f'Found an un-enumerated conflicting pathogenicity: {pathogenicity}')
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
        for c in classified_record_node.findall('TraitMappingList/TraitMapping/MedGen')
        if c.attrib['Name'] != 'not provided'
    })
    return submitters, conditions

def extract_variant_info(elem: xml.etree.ElementTree.Element) -> tuple[models.ClickhouseModel, models.ClickhouseModel, models.ClickhouseModel]:
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
    # Note: this manipulation to an enumerated pathogenicty happens after we parse conflicting pathogenicities.
    # We need the original string to conditionally parse from a different XML location.
    if pathogenicity == CLINVAR_CONFLICTING_DATA_FROM_SUBMITTERS:
        pathogenicity = CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY
    props = {
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
    if grch38 and grch38['chrom'] == 'MT':
        yield GENOME_VERSION_GRCh38, True, dict(
            variant_id=f"M-{grch38['pos']}-{grch38['ref']}-{grch38['alt']}",
            **props,
        )
    if grch37 and grch37['chrom'] != 'MT':
        yield GENOME_VERSION_GRCh37, False, dict(
            variant_id=f"{grch37['chrom']}-{grch37['pos']}-{grch37['ref']}-{grch37['alt']}",
            **props,
        )
    if grch38 and grch38['chrom'] != 'MT':
        yield GENOME_VERSION_GRCh38, False, dict(
            variant_id=f"{grch38['chrom']}-{grch38['pos']}-{grch38['ref']}-{grch38['alt']}",
            **props,
        )

def iter_clinvar_xml_data():
    with requests.get(WEEKLY_XML_RELEASE, stream=True, timeout=10) as r:
        r.raise_for_status()
        for event, elem in ET.iterparse(gzip.GzipFile(fileobj=r.raw), events=('start', 'end',)):
            # Handle parsing the current date.
            if event == 'start' and elem.tag == 'ClinVarVariationRelease':
                new_version = elem.attrib['ReleaseDate']
                yield new_version

            # Handle parsing variants
            if event == 'end' and elem.tag == 'VariationArchive' and new_version:
                for obj in extract_variant_info(elem):
                    yield obj
                elem.clear()
