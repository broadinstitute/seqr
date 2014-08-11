from django import forms
from django.template.defaultfilters import slugify
from django.conf import settings

from xbrowse.utils import get_gene_id_from_str


class GeneListForm(forms.Form):

    name = forms.CharField(max_length=40, required=True)
    description = forms.CharField(max_length=200, required=True)
    is_public = forms.ChoiceField(choices=[('yes', 'Yes'), ('no', 'No')])
    genes = forms.CharField(widget=forms.Textarea, required=True)

    def clean(self):
        cleaned_data = super(GeneListForm, self).clean()

        gene_str_list = cleaned_data['genes'].split()
        gene_ids = []
        gene_id_errors = []
        for s in gene_str_list:
            gene_id = get_gene_id_from_str(s.strip(), get_reference())
            if not gene_id:
                gene_id_errors.append(s)
            gene_ids.append(gene_id)
        if len(gene_id_errors) > 0:
            raise forms.ValidationError("Can't find a gene ID for this gene: %s" % " and ".join(gene_id_errors))
        cleaned_data['gene_ids'] = gene_ids
        cleaned_data['slug'] = slugify(cleaned_data['name'])[:40]
        cleaned_data['is_public'] = cleaned_data['is_public'] == 'yes'

        return cleaned_data

