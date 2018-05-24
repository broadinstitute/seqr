from django.contrib import admin
from models import GeneList


@admin.register(GeneList)
class GeneListAdmin(admin.ModelAdmin):
    fields = ['slug', 'name', 'description']
    search_fields = ['slug', 'name', 'description']
    save_on_top = True
    list_per_page = 2000

