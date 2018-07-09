from collections import defaultdict
from django.db.models.query_utils import Q
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import Http404

from xbrowse.analysis_modules.combine_mendelian_families import get_families_by_gene
from xbrowse_server.base.models import Project, Family, Cohort, FamilyGroup, VariantNote, VariantTag, GeneNote, VariantFunctionalData
from xbrowse_server.analysis import population_controls
from xbrowse import genomeloc
from xbrowse import stream_utils
from xbrowse.variant_search.family import get_variants as get_variants_family, get_genes as get_genes_family, get_variants_with_inheritance_mode, get_variants_allele_count
from xbrowse.variant_search.cohort import get_genes_with_inheritance as cohort_get_genes_with_inheritance
from xbrowse import utils as xbrowse_utils
from xbrowse_server import mall
from xbrowse_server.mall import get_mall, get_reference, get_datastore


def get_project_for_user(user, request_data):
    """
    Get project and family from request data
    Throw 404 if invalid IDs, or if user doesn't have view access
    """
    project = get_object_or_404(Project, project_id=request_data.get('project_id'))
    if not project.can_view(user):
        raise Http404
    return project


def get_project_and_family_for_user(user, request_data):
    """
    Get project and family from request data
    Throw 404 if invalid IDs, or if user doesn't have view access
    """

    project = get_object_or_404(Project, project_id=request_data.get('project_id'))
    family = get_object_or_404(Family, project=project, family_id=request_data.get('family_id'))

    if not project.can_view(user):
        raise Http404

    return project, family


def get_project_and_cohort_for_user(user, request_data):
    """
    Same as above, for cohorts
    """
    project = get_object_or_404(Project, project_id=request_data.get('project_id'))
    cohort = get_object_or_404(Cohort, project=project, cohort_id=request_data.get('cohort_id'))
    if not project.can_view(user):
        raise Http404
    return project, cohort


def get_project_and_family_group_for_user(user, request_data):
    """
    Same as above, for cohorts
    """
    project = get_object_or_404(Project, project_id=request_data.get('project_id'))
    family_group = get_object_or_404(FamilyGroup, project=project, slug=request_data.get('family_group'))
    if not project.can_view(user):
        raise Http404
    return project, family_group


def get_genotype_from_geno_str(geno_str):
    d = {}
    if geno_str == 'ref_ref':
        d['num_alt'] = 0
    elif geno_str == 'ref_alt':
        d['num_alt'] = 1
    elif geno_str == 'alt_alt':
        d['num_alt'] = 2
    elif geno_str == 'missing':
        d['num_alt'] = -1
    return d


def get_gene_id_list_from_raw(raw_text, reference):
    """
    raw_text is a string that contains a list of genes separated by whitespace
    return (success, result)
    if success is true, result is a list of gene_ids that can be used in a variant_filter
    if false, result is a gene_id that could not be converted
    """
    gene_strs = raw_text.split()
    gene_ids = []
    for gene_str in gene_strs:
        if xbrowse_utils.get_gene_id_from_str(gene_str, reference):
            gene_ids.append(xbrowse_utils.get_gene_id_from_str(gene_str, reference))
        else:
            return False, gene_str

    return True, gene_ids


def get_locations_from_raw(region_strs, reference):
    """
    raw_text is a string that contains a list of regions
    return (success, result)
    if success is true, result is a list of (xstart, xstop) pairs that can be used in a variant_filter
    if false, result is a string that could not be converted
    """
    locations = []
    for region_str in region_strs:
        t = genomeloc.get_range_single_location_from_string(region_str)
        if t:
            locations.append(t)
        else:
            return False, region_str

    return True, locations


def add_disease_genes_to_variants(project, variants):
    """
    Take a list of variants and annotate them with disease genes
    """
    by_gene = project.get_gene_list_map()
    gene_lists_map = defaultdict(set)
    for variant in variants:
        gene_lists = []
        for gene_id in variant.coding_gene_ids:
            for g in by_gene[gene_id]:
                gene_lists.append(g.name)
                gene_lists_map[gene_id].add(g.name)
        variant.set_extra('disease_genes', gene_lists)
        for gene_id in variant.extras['genes'].keys():
            variant.extras['genes'][gene_id]['disease_gene_lists'] = list(gene_lists_map.get(gene_id, []))


def add_gene_databases_to_variants(variants):
    """
    Adds variant['gene_databases'] - a list of *gene* databases that this variant's gene(s) are seen in
    """
    for variant in variants:
        variant.set_extra('in_disease_gene_db', False)
        for gene_id in variant.coding_gene_ids:
            gene = get_reference().get_gene(gene_id)
            # TODO: should be part of reference cache
            if gene and 'phenotype_info' in gene and (len(gene['phenotype_info']['orphanet_phenotypes']) or len(gene['phenotype_info']['mim_phenotypes'])):
                variant.set_extra('in_disease_gene_db', True)
                variant.extras['genes'][gene_id]['disease_db_pheotypes'] = gene['phenotype_info']['orphanet_phenotypes'] + gene['phenotype_info']['mim_phenotypes']


def add_gene_names_to_variants(reference, variants):
    """
    Take a list of variants and annotate them with coding genes
    """
    for variant in variants:

        # todo: remove - replace with below
        gene_names = {}
        for gene_id in variant.coding_gene_ids:
            if gene_id:
                gene_names[gene_id] = reference.get_gene_symbol(gene_id)
        if not gene_names:
            for gene_id in variant.gene_ids:
                if gene_id:
                    gene_names[gene_id] = reference.get_gene_symbol(gene_id)
        variant.set_extra('gene_names', gene_names)

        genes = {}
        for gene_id in variant.coding_gene_ids:
            if gene_id:
                genes[gene_id] = reference.get_gene_summary(gene_id)
        if not genes:
            for gene_id in variant.gene_ids:
                if gene_id:
                    genes[gene_id] = reference.get_gene_summary(gene_id)
        variant.set_extra('genes', genes)


def add_family_tags_to_variants(project, variants):
    for variant in variants:
        notes_query = Q(project=project) & Q(xpos=variant.xpos) & Q(ref=variant.ref) & Q(alt=variant.alt)
        if variant.extras.get('family_id'):
            notes_query &= Q(family__family_id=variant.extras['family_id'])
        notes = list(VariantNote.objects.filter(notes_query).order_by('-date_saved').select_related('user__userprofile').only(*VariantNote.VARIANT_JSON_FIELDS))
        variant.set_extra('family_notes', [n.to_variant_json() for n in notes])

        variant_tag_query = Q(project_tag__project=project) & Q(xpos=variant.xpos) & Q(ref=variant.ref) & Q(alt=variant.alt)
        if variant.extras.get('family_id'):
            variant_tag_query &= Q(family__family_id=variant.extras['family_id'])
        tags = list(VariantTag.objects.filter(variant_tag_query).select_related('user__userprofile').select_related('project_tag').only(*VariantTag.VARIANT_JSON_FIELDS))
        variant.set_extra('family_tags', [t.to_variant_json() for t in tags])

        functional_data_query = Q(family__project=project) & Q(xpos=variant.xpos) & Q(ref=variant.ref) & Q(alt=variant.alt)
        if variant.extras.get('family_id'):
            functional_data_query &= Q(family__family_id=variant.extras['family_id'])
        functional_data = list(VariantFunctionalData.objects.filter(functional_data_query).select_related('user__userprofile').only(*VariantFunctionalData.VARIANT_FUNCTIONAL_DATA_JSON_FIELDS))
        variant.set_extra('family_functional_data', [t.to_variant_json() for t in functional_data])


def add_gene_info_to_variants(variants):
    for variant in variants:
        gene_info = {}
        variant.set_extra('gene_info', gene_info)


def add_clinical_info_to_variants(variants):
    for variant in variants:
        xpos, ref, alt = variant.unique_tuple()
        variant_id, clinsig = get_reference().get_clinvar_info(xpos, ref, alt)
        variant.set_extra('clinvar_variant_id', variant_id)
        variant.set_extra('clinvar_clinsig', clinsig)


def add_populations_to_variants(variants, population_slug_list):
    if population_slug_list:
        try:
            mall.get_annotator().get_population_frequency_store().add_populations_to_variants(variants, population_slug_list)
        except Exception, e:
            print("WARNING: got unexpected error in add_custom_populations_to_variants: %s" % e)


def add_custom_populations_to_variants(variants, population_slug_list):
    if population_slug_list:
        mall.get_custom_population_store().add_populations_to_variants(variants, population_slug_list)


def add_extra_info_to_variants_cohort(reference, cohort, variants):
    """
    Add other info to a variant list that client might want to display:
    - disease annotations
    - coding_gene_ids
    """
    add_extra_info_to_variants_project(reference, cohort.project, variants)


def add_extra_info_to_variants_project(reference, project, variants, add_family_tags=False, add_populations=False):
    """
    Add other info to a variant list that client might want to display:
    - disease annotations
    - coding_gene_ids
    """
    if not project.has_elasticsearch_index() or any(v for v in variants if v.get_extra('created_variant')):
        add_gene_names_to_variants(reference, variants)
        add_gene_info_to_variants(variants)
        add_clinical_info_to_variants(variants)
        if add_populations:
            populations = set(
                settings.ANNOTATOR_REFERENCE_POPULATION_SLUGS + project.private_reference_population_slugs())
            missing_pop_variants = [v for v in variants if
                                    v.annotation and not populations.issubset(v.annotation['freqs'])]
            add_populations_to_variants(missing_pop_variants, settings.ANNOTATOR_REFERENCE_POPULATION_SLUGS)
            add_custom_populations_to_variants(missing_pop_variants, project.private_reference_population_slugs())

    add_disease_genes_to_variants(project, variants)
    add_gene_databases_to_variants(variants)
    if add_family_tags:
        add_family_tags_to_variants(project, variants)


def add_notes_to_genes(genes, user):
    for gene in genes:
        notes = GeneNote.objects.filter(gene_id=gene['gene_id']).order_by('date_saved')
        gene['notes'] = [n.toJSON(user) for n in notes]


def add_extra_info_to_genes(project, reference, genes):
    by_gene = project.get_gene_list_map()
    for gene in genes:
        if 'extras' not in gene:
            gene['extras'] = {
                'gene_lists': [],
                'in_disease_gene_db': False,
            }
        if gene['gene_id'] in by_gene:
            gene['extras']['gene_lists'] = [g.name for g in by_gene[gene['gene_id']]]

        xgene = reference.get_gene(gene['gene_id'])
        if xgene and 'phenotype_info' in xgene and (len(xgene['phenotype_info']['orphanet_phenotypes']) or len(xgene['phenotype_info']['mim_phenotypes'])):
            gene['extras']['in_disease_gene_db'] = True


def calculate_cohort_gene_search(cohort, search_spec):
    """
    Calculate search results from the params in search_spec
    Should be called after cache is checked - this does all the computation
    Returns (is_error, genes) tuple
    """
    xcohort = cohort.xcohort()
    cohort_size = len(xcohort.individuals)
    indiv_id_list = xcohort.indiv_id_list()

    genes = []
    for gene_id, indivs_with_inheritance, gene_variation in cohort_get_genes_with_inheritance(
        get_datastore(cohort.project),
        get_reference(),
        xcohort,
        search_spec.inheritance_mode,
        search_spec.variant_filter,
        search_spec.quality_filter,
    ):

        num_hits = len(indivs_with_inheritance)

        # don't return genes with a single variant
        if num_hits < 2:
            continue

        try:
            start_pos, end_pos = get_reference().get_gene_bounds(gene_id)
            chr, start = genomeloc.get_chr_pos(start_pos)
            end = genomeloc.get_chr_pos(end_pos)[1]
        except KeyError:
            chr, start, end = None, None, None

        control_cohort = cohort.project.default_control_cohort if cohort.project.default_control_cohort else settings.DEFAULT_CONTROL_COHORT
        control_comparison = population_controls.control_comparison(
            control_cohort,
            gene_id,
            num_hits,
            cohort_size,
            search_spec.inheritance_mode,
            search_spec.variant_filter,
            search_spec.quality_filter
        )

        xgene = get_reference().get_gene(gene_id)
        if xgene is None:
            continue

        gene = {
            'gene_info': xgene,
            'gene_id': gene_id,
            'gene_name': xgene['symbol'],
            'num_hits': num_hits,
            'num_unique_variants': len(gene_variation.get_relevant_variants_for_indiv_ids(indiv_id_list)),
            'chr': chr,
            'start': start,
            'end': end,
            'control_comparison': control_comparison,
        }

        genes.append(gene)
    return genes


def calculate_mendelian_variant_search(search_spec, family, user=None):
    xfamily = family.xfamily()
    project = family.project
    variants = None
    if search_spec.search_mode == 'standard_inheritance':
        variants = list(get_variants_with_inheritance_mode(
            get_mall(project),
            xfamily,
            search_spec.inheritance_mode,
            variant_filter=search_spec.variant_filter,
            quality_filter=search_spec.quality_filter,
            user=user,
        ))

    elif search_spec.search_mode == 'custom_inheritance':
        variants = list(get_variants_family(
            get_datastore(project),
            xfamily,
            genotype_filter=search_spec.genotype_inheritance_filter,
            variant_filter=search_spec.variant_filter,
            quality_filter=search_spec.quality_filter,
            user=user,
        ))

    elif search_spec.search_mode == 'gene_burden':
        gene_stream = get_genes_family(
            get_datastore(project),
            get_reference(),
            xfamily,
            burden_filter=search_spec.gene_burden_filter,
            variant_filter=search_spec.variant_filter,
            quality_filter=search_spec.quality_filter,
            user=user,
        )

        variants = list(stream_utils.gene_stream_to_variant_stream(gene_stream, get_reference()))

    elif search_spec.search_mode == 'allele_count':
        variants = list(get_variants_allele_count(
            get_datastore(project),
            xfamily,
            search_spec.allele_count_filter,
            variant_filter=search_spec.variant_filter,
            quality_filter=search_spec.quality_filter,
            user=user,
        ))

    elif search_spec.search_mode == 'all_variants':
        variants = list(get_variants_family(
            get_datastore(project),
            xfamily,
            variant_filter=search_spec.variant_filter,
            quality_filter=search_spec.quality_filter,
            indivs_to_consider=xfamily.indiv_id_list(),
            user=user,
        ))

    for variant in variants:
        variant.set_extra('family_id', family.family_id)

    return variants


def calculate_combine_mendelian_families(family_group, search_spec, user=None):
    """
    Calculate search results from the params in search_spec
    Should be called after cache is checked - this does all the computation
    Returns (is_error, genes) tuple
    """
    xfamilygroup = family_group.xfamilygroup()

    genes = []
    for gene_id, family_id_list in get_families_by_gene(
        get_mall(family_group.project),
        xfamilygroup,
        search_spec.inheritance_mode,
        search_spec.variant_filter,
        search_spec.quality_filter,
        user=user,
    ):

        xgene = get_reference().get_gene(gene_id)
        if xgene is None:
            continue

        try:
            start_pos, end_pos = get_reference().get_gene_bounds(gene_id)
            chr, start = genomeloc.get_chr_pos(start_pos)
            end = genomeloc.get_chr_pos(end_pos)[1]
        except KeyError:
            chr, start, end = None, None, None

        gene = {
            'gene_info': xgene,
            'gene_id': gene_id,
            'gene_name': xgene['symbol'],
            'chr': chr,
            'start': start,
            'end': end,
            'family_id_list': family_id_list,
        }

        genes.append(gene)

    return genes

