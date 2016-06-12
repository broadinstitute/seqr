import json

from django import forms
from django.conf import settings

from xbrowse import variant_filters as xbrowse_variant_filters
from xbrowse import quality_filters as xbrowse_quality_filters
from xbrowse.core.variant_filters import VariantFilter
from xbrowse_server.base.models import Family, ProjectTag
from xbrowse.analysis_modules.mendelian_variant_search import MendelianVariantSearchSpec
from xbrowse.analysis_modules.combine_mendelian_families import CombineMendelianFamiliesSpec
from xbrowse.analysis_modules.cohort_gene_search import CohortGeneSearchSpec
from xbrowse.analysis_modules.diagnostic_search import DiagnosticSearchSpec
import utils


# TODO: these forms should return a SearchSpec class - possibly subclasses for each search type
from xbrowse_server.gene_lists.models import GeneList
from xbrowse_server.mall import get_reference


def parse_variant_filter(cleaned_data):
    """
    Sets cleaned_data['variant_filter'] for a form, throwing ValidationError if necessary
    """
    if cleaned_data.get('variant_filter'):
        variant_filter_d = json.loads(cleaned_data.get('variant_filter'))
        if variant_filter_d.get('genes_raw'):
            success, result = utils.get_gene_id_list_from_raw(variant_filter_d.get('genes_raw'), get_reference())
            if not success:
                raise forms.ValidationError("{} is not a recognized gene.".format(result))
            variant_filter_d['genes'] = result
            del variant_filter_d['genes_raw']

        if variant_filter_d.get('regions'):
            success, result = utils.get_locations_from_raw(variant_filter_d.get('regions'), get_reference())
            if not success:
                raise forms.ValidationError("%s is not a recognized region" % result)
            variant_filter_d['locations'] = result
            del variant_filter_d['regions']
        cleaned_data['variant_filter'] = VariantFilter(**variant_filter_d)


def parse_quality_filter(cleaned_data):

    if cleaned_data.get('quality_filter'):
        qf_dict = json.loads(cleaned_data.get('quality_filter'))
        # TODO
        # if 'hom_alt_ratio' in qf_dict:
        #     qf_dict['hom_alt_ratio'] = float(qf_dict['hom_alt_ratio']) / 100
        # if 'het_ratio' in qf_dict:
        #     qf_dict['het_ratio'] = float(qf_dict['het_ratio']) / 100
        cleaned_data['quality_filter'] = qf_dict


def parse_genotype_filter(cleaned_data):
    if cleaned_data.get('genotype_filter'):
        cleaned_data['genotype_filter'] = json.loads(cleaned_data.get('genotype_filter'))


def parse_burden_filter(cleaned_data):
    if cleaned_data.get('burden_filter'):
        cleaned_data['burden_filter'] = json.loads(cleaned_data.get('burden_filter'))


def parse_family_tuple_list(cleaned_data):
    families = []
    family_tuples = json.loads(cleaned_data.get('family_tuple_list'))
    for project_id, family_id in family_tuples:
        families.append(Family.objects.get(project__project_id=project_id, family_id=family_id))
    cleaned_data['families'] = families


def parse_allele_count_filter(cleaned_data):
    if cleaned_data.get('allele_count_filter'):
        json_dict = json.loads(cleaned_data['allele_count_filter'])
        cleaned_data['allele_count_filter'] = xbrowse_variant_filters.AlleleCountFilter(**json_dict)


class MendelianVariantSearchForm(forms.Form):

    search_mode = forms.CharField()
    variant_filter = forms.CharField(required=False)
    quality_filter = forms.CharField(required=False)

    inheritance_mode = forms.CharField(required=False)
    genotype_filter = forms.CharField(required=False)
    burden_filter = forms.CharField(required=False)
    allele_count_filter = forms.CharField(required=False)

    def clean(self):

        cleaned_data = super(MendelianVariantSearchForm, self).clean()

        if cleaned_data['search_mode'] not in ['standard_inheritance', 'custom_inheritance', 'gene_burden', 'allele_count', 'all_variants']:
            raise forms.ValidationError("Invalid search mode: {}".format(cleaned_data['search_mode']))

        if cleaned_data['search_mode'] == 'standard_inheritance' and not cleaned_data.get('inheritance_mode'):
            raise forms.ValidationError("Inheritance mode is required for standard search. ")

        parse_variant_filter(cleaned_data)
        parse_quality_filter(cleaned_data)
        parse_genotype_filter(cleaned_data)
        parse_burden_filter(cleaned_data)
        parse_allele_count_filter(cleaned_data)

        search_spec = MendelianVariantSearchSpec()
        search_spec.search_mode = cleaned_data['search_mode']
        search_spec.inheritance_mode = cleaned_data.get('inheritance_mode')
        search_spec.genotype_inheritance_filter = cleaned_data.get('genotype_filter')
        search_spec.gene_burden_filter = cleaned_data.get('burden_filter')
        search_spec.allele_count_filter = cleaned_data.get('allele_count_filter')
        search_spec.variant_filter = cleaned_data.get('variant_filter')
        search_spec.quality_filter = cleaned_data.get('quality_filter')
        cleaned_data['search_spec'] = search_spec

        return cleaned_data


class CohortVariantSearchForm(forms.Form):

    search_mode = forms.CharField()
    inheritance_mode = forms.CharField(required=False)
    variant_filter = forms.CharField(required=False)
    quality_filter = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super(CohortVariantSearchForm, self).clean()
        parse_variant_filter(cleaned_data)
        parse_quality_filter(cleaned_data)

        search_spec = MendelianVariantSearchSpec()
        search_spec.search_mode = cleaned_data['search_mode']
        search_spec.inheritance_mode = cleaned_data.get('inheritance_mode')
        search_spec.variant_filter = cleaned_data.get('variant_filter')
        search_spec.quality_filter = cleaned_data.get('quality_filter')
        cleaned_data['search_spec'] = search_spec

        return cleaned_data


class CohortGeneSearchForm(forms.Form):

    inheritance_mode = forms.CharField()
    variant_filter = forms.CharField(required=False)
    quality_filter = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super(CohortGeneSearchForm, self).clean()

        parse_variant_filter(cleaned_data)
        parse_quality_filter(cleaned_data)

        search_spec = CohortGeneSearchSpec()
        search_spec.inheritance_mode = cleaned_data.get('inheritance_mode')
        search_spec.variant_filter = cleaned_data.get('variant_filter')
        search_spec.quality_filter = cleaned_data.get('quality_filter')
        cleaned_data['search_spec'] = search_spec

        return cleaned_data


class CohortGeneSearchVariantsForm(CohortGeneSearchForm):

    gene_id = forms.CharField()

    def clean(self):
        cleaned_data = super(CohortGeneSearchVariantsForm, self).clean()
        if not get_reference().is_valid_gene_id(cleaned_data['gene_id']):
            raise forms.ValidationError("{} is not a valid gene ID".format(cleaned_data['gene_id']))
        return cleaned_data


class CombineMendelianFamiliesForm(forms.Form):

    inheritance_mode = forms.CharField()
    variant_filter = forms.CharField(required=False)
    quality_filter = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super(CombineMendelianFamiliesForm, self).clean()
        parse_variant_filter(cleaned_data)
        parse_quality_filter(cleaned_data)

        search_spec = CombineMendelianFamiliesSpec()
        search_spec.inheritance_mode = cleaned_data.get('inheritance_mode')
        search_spec.variant_filter = cleaned_data.get('variant_filter')
        search_spec.quality_filter = cleaned_data.get('quality_filter')
        cleaned_data['search_spec'] = search_spec

        return cleaned_data


class CombineMendelianFamiliesVariantsForm(forms.Form):

    inheritance_mode = forms.CharField()
    gene_id = forms.CharField()
    family_tuple_list = forms.CharField()
    variant_filter = forms.CharField(required=False)
    quality_filter = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super(CombineMendelianFamiliesVariantsForm, self).clean()
        parse_variant_filter(cleaned_data)
        parse_quality_filter(cleaned_data)
        parse_family_tuple_list(cleaned_data)

        if not get_reference().is_valid_gene_id(cleaned_data['gene_id']):
            raise forms.ValidationError("{} is not a valid gene ID".format(cleaned_data['gene_id']))

        return cleaned_data

# class VariantInfoForm(forms.Form):
#
#     xpos = forms.CharField()
#     ref = forms.CharField()
#     alt = forms.CharField()
#
#     def clean(self):
#         cleaned_data = super(VariantInfoForm, self).clean()
#         cleaned_data['xpos'] = int()



class DiagnosticSearchForm(forms.Form):

    gene_list_slug = forms.CharField()
    variant_filter = forms.CharField(required=False)

    def __init__(self, family, *args, **kwargs):
        super(DiagnosticSearchForm, self).__init__(*args, **kwargs)
        self.family = family

    def clean(self):
        cleaned_data = super(DiagnosticSearchForm, self).clean()
        parse_variant_filter(cleaned_data)
        cleaned_data['gene_list'] = GeneList.objects.get(slug=cleaned_data.get('gene_list_slug'))

        search_spec = DiagnosticSearchSpec()
        search_spec.inheritance_mode = cleaned_data.get('inheritance_mode')
        search_spec.variant_filter = cleaned_data.get('variant_filter')
        search_spec.gene_ids = cleaned_data['gene_list'].gene_id_list()
        cleaned_data['search_spec'] = search_spec

        return cleaned_data


class VariantNoteForm(forms.Form):
    note_text = forms.CharField(max_length=1000)
    xpos = forms.CharField(max_length=20)
    ref = forms.CharField(max_length=1000)
    alt = forms.CharField(max_length=1000)
    note_id = forms.CharField(max_length=10, widget=forms.HiddenInput, required=False)

    def __init__(self, project, *args, **kwargs):
        super(VariantNoteForm, self).__init__(*args, **kwargs)
        self.project = project

    def clean(self):
        cleaned_data = super(VariantNoteForm, self).clean()
        cleaned_data['xpos'] = int(cleaned_data['xpos'])
        return cleaned_data


class VariantTagsForm(forms.Form):
    tag_slugs = forms.CharField(max_length=1000, required=False)
    xpos = forms.CharField(max_length=20)
    ref = forms.CharField(max_length=1000)
    alt = forms.CharField(max_length=1000)
    search_url = forms.CharField(max_length=2000,widget=forms.HiddenInput, required=False)

    def __init__(self, project, *args, **kwargs):
        super(VariantTagsForm, self).__init__(*args, **kwargs)
        self.project = project

    def clean(self):
        cleaned_data = super(VariantTagsForm, self).clean()
        cleaned_data['xpos'] = int(cleaned_data['xpos'])
        cleaned_data['project_tags'] = []
        for tag_text in cleaned_data['tag_slugs'].split('|'):
            if not tag_text:
                continue
            cleaned_data['project_tags'].append(ProjectTag.objects.get(project=self.project, tag=tag_text))
        return cleaned_data
