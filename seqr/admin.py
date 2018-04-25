from django.contrib import admin
from seqr.models import Project, Family, Individual, Sample, Dataset, \
    LocusList, LocusListGene, LocusListInterval, VariantNote, VariantTag, VariantTagType

for m in [Project, Family, Individual, Sample, Dataset, LocusList, LocusListGene, LocusListInterval,
          VariantNote, VariantTag, VariantTagType]:
    admin.site.register(m)