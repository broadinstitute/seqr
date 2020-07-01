from __future__ import unicode_literals

import logging
from collections import defaultdict
from datetime import datetime
from django.db.models import prefetch_related_objects, Q

from reference_data.models import HumanPhenotypeOntology
from matchmaker.models import MatchmakerSubmission, MatchmakerIncomingQuery, MatchmakerResult
from seqr.utils.gene_utils import get_genes, get_gene_ids_for_gene_symbols, get_filtered_gene_ids
from settings import MME_DEFAULT_CONTACT_INSTITUTION

logger = logging.getLogger(__name__)


def get_mme_genes_phenotypes_for_results(results, **kwargs):
    return _get_mme_genes_phenotypes(
        results, _get_patient_features, _get_patient_genomic_features, include_matched_symbol_genes=True,  **kwargs)


def get_mme_genes_phenotypes_for_submissions(submissions):
    return _get_mme_genes_phenotypes(submissions, _get_submisson_features, _get_submisson_genomic_features)


def _get_patient_features(result):
    return result['patient'].get('features')


def _get_patient_genomic_features(result):
    return result['patient'].get('genomicFeatures')


def _get_submisson_features(submisson):
    return submisson.features


def _get_submisson_genomic_features(submisson):
    return submisson.genomic_features


def _get_mme_gene_phenotype_ids(results, get_features, get_genomic_features, additional_genes=None, additional_hpo_ids=None):
    hpo_ids = additional_hpo_ids if additional_hpo_ids else set()
    genes = additional_genes if additional_genes else set()
    for result in results:
        hpo_ids.update({feature['id'] for feature in (get_features(result) or []) if feature.get('id')})
        genes.update({gene_feature['gene']['id'] for gene_feature in (get_genomic_features(result) or [])
                      if gene_feature.get('gene', {}).get('id')})

    gene_ids = {gene for gene in genes if gene.startswith('ENSG')}
    gene_symols = {gene for gene in genes if not gene.startswith('ENSG')}
    return hpo_ids, gene_ids, gene_symols


def _get_mme_genes_phenotypes(results, get_features, get_genomic_features, include_matched_symbol_genes=False, **kwargs):
    hpo_ids, gene_ids, gene_symbols = _get_mme_gene_phenotype_ids(results, get_features, get_genomic_features, **kwargs)
    gene_symbols_to_ids = get_gene_ids_for_gene_symbols(gene_symbols)
    if include_matched_symbol_genes:
        # Include all gene IDs associated with the given symbol
        for new_gene_ids in gene_symbols_to_ids.values():
            gene_ids.update(new_gene_ids)
        # Include any gene IDs whose legacy id is the given symbol
        for gene_symbol in gene_symbols:
            legacy_gene_ids = get_filtered_gene_ids(
                Q(dbnsfpgene__gene_names__startswith='{};'.format(gene_symbol)) |
                Q(dbnsfpgene__gene_names__endswith=';{}'.format(gene_symbol)) |
                Q(dbnsfpgene__gene_names__contains=';{};'.format(gene_symbol))
            )
            gene_symbols_to_ids[gene_symbol] += legacy_gene_ids
            gene_ids.update(legacy_gene_ids)
    else:
        gene_ids.update({new_gene_ids[0] for new_gene_ids in gene_symbols_to_ids.values()})

    genes_by_id = get_genes(gene_ids)

    hpo_terms_by_id = {hpo.hpo_id: hpo.name for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=hpo_ids)}

    return hpo_terms_by_id, genes_by_id, gene_symbols_to_ids


def parse_mme_features(features, hpo_terms_by_id):
    phenotypes = [feature for feature in (features or [])]
    for feature in phenotypes:
        feature['label'] = hpo_terms_by_id.get(feature['id'])
    return phenotypes


def parse_mme_gene_variants(genomic_features, gene_symbols_to_ids):
    gene_variants = []
    for gene_feature in (genomic_features or []):
        gene_ids = get_gene_ids_for_feature(gene_feature, gene_symbols_to_ids)
        gene_id = gene_ids[0] if gene_ids else None
        if gene_id:
            gene_variant = {'geneId': gene_id}
            if gene_feature.get('variant'):
                gene_variant.update({
                    'alt': gene_feature['variant'].get('alternateBases'),
                    'ref': gene_feature['variant'].get('referenceBases'),
                    'chrom': gene_feature['variant'].get('referenceName'),
                    'pos': gene_feature['variant'].get('start'),
                    'genomeVersion': gene_feature['variant'].get('assembly'),
                })
            gene_variants.append(gene_variant)
    return gene_variants


def get_gene_ids_for_feature(gene_feature, gene_symbols_to_ids):
    gene_id = gene_feature.get('gene', {}).get('id')
    if not gene_id:
        return []
    if not gene_id.startswith('ENSG'):
        gene_ids = gene_symbols_to_ids.get(gene_feature['gene']['id'], [])
    else:
        gene_ids = [gene_id]
    return gene_ids


def parse_mme_patient(result, hpo_terms_by_id, gene_symbols_to_ids, submission_guid):
    phenotypes = parse_mme_features(_get_patient_features(result), hpo_terms_by_id)
    gene_variants = parse_mme_gene_variants(_get_patient_genomic_features(result), gene_symbols_to_ids)

    parsed_result = {
        'geneVariants': gene_variants,
        'phenotypes': phenotypes,
        'submissionGuid': submission_guid,
    }
    parsed_result.update(result)
    return parsed_result


def get_submission_json_for_external_match(submission, score=None):
    submission_json = {
        'patient': {
            'id': submission.submission_id,
            'label': submission.label,
            'contact': {
                'href': submission.contact_href.replace(' ', ''),
                'name': submission.contact_name,
                'institution': MME_DEFAULT_CONTACT_INSTITUTION,
            },
            'species': 'NCBITaxon:9606',
            'features': submission.features,
            'genomicFeatures': submission.genomic_features,
        }
    }
    sex = MatchmakerSubmission.SEX_LOOKUP.get(submission.individual.sex)
    if sex:
        submission_json['patient']['sex'] = sex
    if score:
        submission_json['score'] = score
    return submission_json


def get_mme_matches(patient_data, origin_request_host=None, user=None):
    hpo_terms_by_id, genes_by_id, gene_symbols_to_ids = get_mme_genes_phenotypes_for_results([patient_data])

    genomic_features = _get_patient_genomic_features(patient_data)
    feature_ids = [
        feature['id'] for feature in (_get_patient_features(patient_data) or []) if
        feature.get('observed', 'yes') == 'yes' and feature['id'] in hpo_terms_by_id
    ]

    if genomic_features:
        for feature in genomic_features:
            feature['gene_ids'] = get_gene_ids_for_feature(feature, gene_symbols_to_ids)
        get_submission_kwargs = {
            'query_ids': list(genes_by_id.keys()),
            'filter_key': 'genomic_features',
            'id_filter_func': lambda gene_id: {'gene': {'id': gene_id}},
        }
    else:
        get_submission_kwargs = {
            'query_ids': feature_ids,
            'filter_key': 'features',
            'id_filter_func': lambda feature_id: {'id': feature_id, 'observed': 'yes'},
        }

    query_patient_id = patient_data['patient']['id']
    scored_matches = _get_matched_submissions(
        query_patient_id,
        get_match_genotype_score=lambda match: _get_genotype_score(genomic_features, match) if genomic_features else 0,
        get_match_phenotype_score=lambda match: _get_phenotype_score(feature_ids, match) if feature_ids else 0,
        **get_submission_kwargs
    )

    incoming_query = MatchmakerIncomingQuery.objects.create(
        institution=patient_data['patient']['contact'].get('institution') or origin_request_host,
        patient_id=query_patient_id if scored_matches else None,
    )
    if not scored_matches:
        return [], incoming_query

    prefetch_related_objects(list(scored_matches.keys()), 'matchmakerresult_set')
    for match_submission in scored_matches.keys():
        if not match_submission.matchmakerresult_set.filter(result_data__patient__id=query_patient_id):
            MatchmakerResult.objects.create(
                submission=match_submission,
                originating_query=incoming_query,
                result_data=patient_data,
                last_modified_by=user,
            )

    return [get_submission_json_for_external_match(match_submission, score=score)
            for match_submission, score in scored_matches.items()], incoming_query


def _get_matched_submissions(patient_id, get_match_genotype_score, get_match_phenotype_score, query_ids, filter_key, id_filter_func):
    if not query_ids:
        # no valid entities found for provided features
        return {}

    matches = []
    for item_id in query_ids:
        matches += MatchmakerSubmission.objects.filter(**{
            '{}__contains'.format(filter_key): [id_filter_func(item_id)]
        }).exclude(submission_id=patient_id)

    scored_matches = {}
    for match in matches:
        genotype_score = get_match_genotype_score(match)
        phenotype_score = get_match_phenotype_score(match)

        if genotype_score > 0 or phenotype_score > 0.65:
            scored_matches[match] = {
                '_genotypeScore': genotype_score,
                '_phenotypeScore': phenotype_score,
                'patient': 1 if genotype_score == 1 else round(genotype_score * (phenotype_score or 1), 4)
            }
    return scored_matches


def _get_genotype_score(genomic_features, match):
    match_features_by_gene_id = defaultdict(list)
    for feature in match.genomic_features:
        match_features_by_gene_id[feature['gene']['id']].append(feature)

    score = 0
    for feature in genomic_features:
        feature_gene_matches = []
        for gene_id in feature['gene_ids']:
            feature_gene_matches += match_features_by_gene_id[gene_id]
        if feature_gene_matches:
            score += 0.7
            if feature.get('zygosity') and any(
                    match_feature.get('zygosity') == feature['zygosity'] for match_feature in feature_gene_matches
            ):
                score += 0.15
            if feature.get('variant') and any(
                    _is_same_variant(feature['variant'], match_feature['variant'])
                    for match_feature in feature_gene_matches if match_feature.get('variant')
            ):
                score += 0.15
    return float(score) / len(genomic_features)


def _is_same_variant(var1, var2):
    for field in {'alternateBases', 'referenceBases', 'referenceName', 'start', 'assembly'}:
        if var1.get(field) and var1.get(field) != var2.get(field):
            return False
    return True


def _get_phenotype_score(hpo_ids, match):
    if not match.features:
        return 0.5
    matched_hpo_ids = [
        hpo_id for hpo_id in hpo_ids
        if any(feature['id'] == hpo_id and feature.get('observed', 'yes') == 'yes' for feature in match.features)
    ]
    return float(len(matched_hpo_ids)) / len(hpo_ids) or 0.1


def get_mme_metrics():
    submissions = MatchmakerSubmission.objects.filter(deleted_date__isnull=True)

    hpo_ids, gene_ids, gene_symols = _get_mme_gene_phenotype_ids(
        submissions, _get_submisson_features, _get_submisson_genomic_features
    )
    if gene_symols:
        logger.error('Found unexpected gene in MME: {}'.format(', '.join(gene_symols)))

    submitters = set()
    for submission in submissions:
        submitters.update({name.strip() for name in submission.contact_name.split(',')})

    incoming_request_count = MatchmakerIncomingQuery.objects.count()
    matched_incoming_request_count = MatchmakerIncomingQuery.objects.filter(
        patient_id__isnull=False).distinct('patient_id').count()

    return {
        "numberOfCases": submissions.count(),
        "numberOfSubmitters": len(submitters),
        "numberOfUniqueGenes": len(gene_ids),
        "numberOfUniqueFeatures": len(hpo_ids),
        "numberOfRequestsReceived": incoming_request_count,
        "numberOfPotentialMatchesSent": matched_incoming_request_count,
        "dateGenerated": datetime.now().strftime('%Y-%m-%d'),
    }


MME_DISCLAIMER = """The data in Matchmaker Exchange is provided for research use only. Broad Institute provides the data
in Matchmaker Exchange 'as is'. Broad Institute makes no representations or warranties of any kind concerning the data,
express or implied, including without limitation, warranties of merchantability, fitness for a particular purpose,
noninfringement, or the absence of latent or other defects, whether or not discoverable. Broad will not be liable to the
user or any third parties claiming through user, for any loss or damage suffered through the use of Matchmaker Exchange.
In no event shall Broad Institute or its respective directors, officers, employees, affiliated investigators and
affiliates be liable for indirect, special, incidental or consequential damages or injury to property and lost profits,
regardless of whether the foregoing have been advised, shall have other reason to know, or in fact shall know of the
possibility of the foregoing. Prior to using Broad Institute data in a publication, the user will contact the owner of
the matching dataset to assess the integrity of the match. If the match is validated, the user will offer appropriate
recognition of the data owner's contribution, in accordance with academic standards and custom. Proper acknowledgment
shall be made for the contributions of a party to such results being published or otherwise disclosed, which may include
co-authorship. If Broad Institute contributes to the results being published, the authors must acknowledge Broad
Institute using the following wording: 'This study makes use of data shared through the Broad Institute matchbox
repository. Funding for the Broad Institute was provided in part by National Institutes of Health grant UM1 HG008900 to
Daniel MacArthur and Heidi Rehm.' User will not attempt to use the data or Matchmaker Exchange to establish the
individual identities of any of the subjects from whom the data were obtained. This applies to matches made within Broad
Institute or with any other database included in the Matchmaker Exchange.""".replace('\n', ' ')
