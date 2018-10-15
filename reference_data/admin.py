from copy import deepcopy
from django.contrib import admin
from django.core.exceptions import FieldDoesNotExist
from reference_data.models import GeneInfo, HumanPhenotypeOntology, dbNSFPGene, GeneConstraint, GeneExpression, \
    TranscriptInfo, Omim


def get_gene_symbol(obj):
    return obj.gene.gene_symbol
get_gene_symbol.short_description = 'Gene Symbol'
get_gene_symbol.admin_order_field = 'gene__gene_symbol'


def get_gene_id(obj):
    return obj.gene.gene_id
get_gene_id.short_description = 'Gene Id'
get_gene_id.admin_order_field = 'gene__gene_id'


for model_class in [GeneInfo, HumanPhenotypeOntology, dbNSFPGene, GeneConstraint, GeneExpression, TranscriptInfo, Omim]:
    @admin.register(model_class)
    class SpecificModelAdmin(admin.ModelAdmin):
        search_fields = deepcopy(model_class._meta.json_fields if hasattr(model_class._meta, 'json_fields') else [])
        list_display = [field.name for field in model_class._meta.get_fields() if not (field.is_relation or field.name == 'id')]
        try:
            model_class._meta.get_field('gene')
            search_fields += ['gene__gene_id', 'gene__gene_symbol']
            list_display = [get_gene_symbol, get_gene_id] + list_display
        except FieldDoesNotExist:
            pass
        save_on_top = True
        list_per_page = 2000
