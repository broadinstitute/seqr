from django.conf import settings
from django.core.management import BaseCommand
from xbrowse_server import mall
from xbrowse_server.mall import get_reference, get_datastore, get_project_datastore
from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator
from xbrowse_server.base.models import Project
import annotator_settings
import sqlite3
import datetime

class Command(BaseCommand):
    def load_population_frequency_store(self):
        population_frequency_store = mall.get_annotator().get_population_frequency_store()
        for population_spec in annotator_settings.reference_populations_to_load:
            print("Loading " + str(population_spec))
            population_frequency_store.load_population(population_spec)

    def update_pop_freqs_in_family_tables(self):
        # Load family tables
        population_frequency_store = mall.get_annotator().get_population_frequency_store()

        db = sqlite3.connect("reference_populations_family_tables.db", isolation_level=None)
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




    def update_pop_freqs_in_project_tables(self):
        # Load project tables
        population_frequency_store = mall.get_annotator().get_population_frequency_store()

        db = sqlite3.connect("reference_populations_project_tables.db", isolation_level=None)
        db.execute("CREATE TABLE if not exists all_projects(project_id varchar(200), started bool, finished bool)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS all_projects_idx ON all_projects(project_id)")

        
        import random        
        other_project_ids = [p.project_id for p in Project.objects.all() if p.project_id != "myoseq_v11"]
        random.shuffle(other_project_ids)
        project_ids = ["myoseq_v11"] + other_project_ids
        for project_id in project_ids:
            db.execute("INSERT OR IGNORE INTO all_projects VALUES (?, 0, 0)", (project_id,))


        # Go through each project and update the variant records
        population_slugs_to_load = [population_spec['slug'] for population_spec in annotator_settings.reference_populations]
        while True:
            remaining_work = list(db.execute("SELECT project_id FROM all_projects WHERE started=0"))
            print("%d projects remaining" % len(remaining_work))
            if not remaining_work:
                print("Done with all projects")
                break

            project_id, = remaining_work[0]
            project_store = get_project_datastore(project_id)


            print("    updating %s " % project_id)
            db.execute("UPDATE all_projects SET started=1 WHERE project_id=?", (project_id,))

            project_collection = project_store._get_project_collection(project_id)
            for variant_dict in project_collection.find():
                freqs = population_frequency_store.get_frequencies(variant_dict['xpos'], variant_dict['ref'], variant_dict['alt'])
                full_freqs = {'db_freqs.'+population_slug: freqs.get(population_slug, 0) for population_slug in population_slugs_to_load}
                project_collection.update({'xpos':variant_dict['xpos'], 'ref' :variant_dict['ref'], 'alt': variant_dict['alt']},
                                         {'$set': full_freqs},
                                         upsert=False)

            print("     ---> done updating project_id: %s" % project_id)
            db.execute("UPDATE all_projects SET finished=1 WHERE project_id=?", (project_id,))

    def update_annotator_variants_table(self):
        """Updates all db.variants population frequencies based on population_frequency"""

        population_frequency_store = mall.get_annotator().get_population_frequency_store()
        population_slugs_to_load = [population_spec['slug'] for population_spec in annotator_settings.reference_populations]

        annotator_store = mall.get_annotator().get_annotator_datastore()

        counter = 0
        for variant_dict in annotator_store.variants.find():
            counter += 1
            if counter % 10000 == 0:
                print("%s: %s processed" % (datetime.datetime.now(), counter))

            freqs = population_frequency_store.get_frequencies(variant_dict['xpos'], variant_dict['ref'], variant_dict['alt'])
            full_freqs = {'annotation.freqs.'+population_slug: freqs.get(population_slug, 0) for population_slug in population_slugs_to_load}

            if sum(full_freqs.values()) > 0:
                # only update if atleast one of the freqs is > 0
                annotator_store.variants.update({'xpos':variant_dict['xpos'], 'ref': variant_dict['ref'], 'alt': variant_dict['alt']},
                               {'$set': full_freqs},
                               upsert=False)

            #print("Running on: " + str(variant_dict))
            #print(full_freqs)
            #print(annotator_store.variants.find({'xpos':variant_dict['xpos'], 'ref': variant_dict['ref'], 'alt': variant_dict['alt']}).next())
            #print("------")

    def handle(self, *args, **options):
        self.load_population_frequency_store()
        #self.update_pop_freqs_in_family_tables()
        #self.update_pop_freqs_in_project_tables()
        self.update_annotator_variants_table()


    # "db_freqs" : { "g1k_all" : 0, "exac" : 0 },
