from django.conf import settings
from django.core.management import BaseCommand
from xbrowse_server import mall
from xbrowse_server.mall import get_reference, get_datastore
from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator
from xbrowse_server.base.models import Project
import annotator_settings
import sqlite3

class Command(BaseCommand):
    def handle(self, *args, **options):
        population_frequency_store = mall.get_annotator().get_population_frequency_store()
        for population_spec in annotator_settings.reference_populations_to_load:
            print("Loading " + str(population_spec))
            #population_frequency_store.load_population(population_spec)
            
        db = sqlite3.connect("load_reference_populations.db", isolation_level=None)
        db.execute("CREATE TABLE if not exists all_projects(project_id varchar(200), family_id varchar(200), started bool, finished bool)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS all_projects_idx ON all_projects(project_id, family_id)")
        for project in Project.objects.all().order_by('-last_accessed_date'):
            project_id = project.project_id
            datastore = get_datastore(project_id)
            for i, family_info in enumerate(datastore._get_family_info(project_id)):
                family_id = family_info['family_id']
                db.execute("INSERT OR IGNORE INTO all_projects VALUES (?, ?, 0, 0)", (project_id, family_id))

        # Go through each project in decending order
        population_slugs_to_load = [population_spec['slug'] for population_spec in annotator_settings.reference_populations_to_load]
        while True:
            remaining_work = list(db.execute("SELECT project_id, family_id FROM all_projects WHERE started=0 ORDER BY RANDOM()"))
            print("%d projects / families remaining" % len(remaining_work))
            if not remaining_work:
                print("Done with all projects/families")
                break

            project_id, family_id = remaining_work[0]
            datastore = get_datastore(project_id)
            print("    updating %s / %s" % (project_id, family_id))
            db.execute("UPDATE all_projects SET started=1 WHERE project_id=? AND family_id=?", (project_id, family_id))

            family_collection = datastore._get_family_collection(project_id, family_id)
             
            for variant_dict in family_collection.find():
                freqs = population_frequency_store.get_frequencies(variant_dict['xpos'], variant_dict['ref'], variant_dict['alt'])
                full_freqs = {'db_freqs.'+population_slug: freqs.get(population_slug, 0) for population_slug in population_slugs_to_load}
                family_collection.update({'xpos':variant_dict['xpos'], 'ref' :variant_dict['ref'], 'alt': variant_dict['alt']}, 
                                         {'$set': full_freqs},
                                         upsert=False)
                #print("---------\nvariant_dict: %s, \nfreqs: %s, \nupdated_variant_dict: %s" % (variant_dict, full_freqs, str(family_collection.find_one(
                #            {'xpos':variant_dict['xpos'], 'ref' :variant_dict['ref'], 'alt': variant_dict['alt']}))))
            

            print("     ---> done updating project_id: %s, family_id: %s" % (project_id, family_id))
            db.execute("UPDATE all_projects SET finished=1 WHERE project_id=? AND family_id=?", (project_id, family_id))

