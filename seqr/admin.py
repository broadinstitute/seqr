from django.contrib import admin
from seqr.models import Project, Family, Individual, Sample, Dataset, \
    LocusList, LocusListGene, LocusListInterval, VariantNote, VariantTag, VariantTagType, VariantFunctionalData, SavedVariant

for model_class in [
    Project,
    Family,
    Individual,
    Sample,
    Dataset,
    LocusList,
    LocusListGene,
    LocusListInterval,
    VariantNote,
    VariantTag,
    VariantTagType,
    VariantFunctionalData,
    SavedVariant,
]:

    @admin.register(model_class)
    class SpecificModelAdmin(admin.ModelAdmin):
        search_fields = [field.name for field in model_class._meta.get_fields() if field.name in set([
            'guid', 'name', 'display_name', 'deprecated_project_id', 'family_id', 'individual_id', 'description'
        ])]
        list_display = search_fields + ['created_date']
        save_on_top = True
        list_per_page = 2000
