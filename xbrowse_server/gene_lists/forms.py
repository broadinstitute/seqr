from crispy_forms.bootstrap import StrictButton
from crispy_forms.layout import Layout
from django import forms
from django.template.defaultfilters import slugify
from django.conf import settings
from crispy_forms.helper import FormHelper

from xbrowse.utils import get_gene_id_from_str
from xbrowse_server.mall import get_reference


class GeneListForm(forms.Form):

    name = forms.CharField(max_length=40, required=True, help_text='Give your gene list a descriptive name')
    description = forms.CharField(max_length=200, required=False, help_text='Some background on how this list is curated')
    is_public = forms.ChoiceField(
        choices=[('yes', 'Yes'), ('no', 'No')],
        help_text='Should other seqr users be able to use this gene list?',
        initial='no',
        required=True,
    )
    genes = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        super(GeneListForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.form_method = 'post'
        self.helper.form_action = '#'
        self.helper.layout = Layout(
            'name',
            'description',
            'is_public',
            'genes',
            StrictButton('Submit', style="margin: 30px 0px", css_class='btn-primary btn-lg col-lg-offset-2', type='submit'),
        )

    def clean(self):
        cleaned_data = super(GeneListForm, self).clean()

        gene_str_list = cleaned_data.get('genes', '').split()
        gene_ids = []
        gene_id_errors = []
        for s in gene_str_list:
            gene_id = get_gene_id_from_str(s.strip(), get_reference())
            if not gene_id:
                gene_id_errors.append(s)
            gene_ids.append(gene_id)
        if len(gene_id_errors) > 0:
            raise forms.ValidationError("Can't find gene(s): %s" % ", ".join(gene_id_errors))
        cleaned_data['gene_ids'] = gene_ids
        cleaned_data['slug'] = slugify(cleaned_data['name'])[:40]
        cleaned_data['is_public'] = cleaned_data['is_public'] == 'yes'

        return cleaned_data

