from django.core import serializers
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ProjectCollaborator, Project, \
    Family, FamilyImageSlide, Cohort, Individual, \
    FamilySearchFlag, ProjectPhenotype, IndividualPhenotype, FamilyGroup, \
    CausalVariant, ProjectTag, VariantTag, VariantNote, ReferencePopulation, \
    UserProfile, VCFFile, ProjectGeneList
from xbrowse_server.mall import get_project_datastore, get_datastore
from pprint import pprint
from xbrowse_server import sample_management

def update(mongo_collection, match_json, set_json):
    print("-----")
    print("updating %s to %s" % (match_json, set_json))
    #return 
    update_result = mongo_collection.update_many(match_json, {'$set': set_json})
    print("updated %s out of %s records" % (update_result.modified_count, update_result.matched_count))
    return update_result

def update_family_analysis_status(project_id):
    for family in Family.objects.filter(project__project_id=project_id):
        if family.analysis_status == "Q" and family.get_data_status() == "loaded":
            print("Setting family %s to Analysis in Progress" % family.family_id)
            family.analysis_status = "I" # switch status from Waiting for Data to Analysis in Progress
            family.save()

def check_that_exists(mongo_collection, match_json, not_more_than_one=False):
    #return 
    records = list(mongo_collection.find(match_json))
    if len(records) == 0:
        print("%s query %s matched 0 records" % (mongo_collection, match_json))
        return False
    if not_more_than_one and len(records) > 1:      
        print("%s query %s matched more than one record: %s" % (mongo_collection, match_json, records))
        return False
    print("-----")
    print("%s query %s returned %s record(s): \n%s" % (mongo_collection, match_json, len(records), "\n".join(map(str, records))))
    return True


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-d', '--destination-project', help="project id to which to transfer the datasets", required=True)
        parser.add_argument('-f', '--from-project', help="project id from which to take the datatsets", required=True)


    def transfer_project(self, from_project_id, destination_project_id):
        print("From: " + from_project_id)
        print("To: " + destination_project_id)

        from_project = Project.objects.get(project_id=from_project_id)
        destination_project = Project.objects.get(project_id=destination_project_id)
        
        # Make sure individuals are the same
        indivs_missing_from_dest_project = (set(
            [i.indiv_id for i in Individual.objects.filter(project=from_project)]) - set(
            [i.indiv_id for i in Individual.objects.filter(project=destination_project)]))
        if indivs_missing_from_dest_project:
            raise Exception("Individuals missing from dest project: " + str(indivs_missing_from_dest_project))
        

        # update VCFs
        vcfs = from_project.families_by_vcf().keys()
        for vcf_file_path in vcfs:            
            vcf_file = VCFFile.objects.get_or_create(file_path=os.path.abspath(vcf_file_path))[0]
            sample_management.add_vcf_file_to_project(destination_project, vcf_file)
            print("Added %s to project %s" % (vcf_file, destination_project.project_id))

        families_db = get_datastore()._db
        projects_db = get_project_datastore()._db

        print("==========")
        print("Checking 'from' Projects and Families:")
        if not check_that_exists(projects_db.projects, {'project_id': from_project_id}, not_more_than_one=True):
            raise ValueError("There needs to be 1 project db in %(from_project_id)s" % locals())
        if not check_that_exists(families_db.families, {'project_id': from_project_id}, not_more_than_one=False):
            raise ValueError("There needs to be atleast 1 family db in %(from_project_id)s" % locals())

        print("==========")
        print("Make Updates:")
        datestamp = datetime.now().strftime("%Y-%m-%d")
        if check_that_exists(projects_db.projects, {'project_id': destination_project_id}, not_more_than_one=True):
            result = update(projects_db.projects, {'project_id': destination_project_id}, {'project_id': destination_project_id+'_previous', 'version': datestamp})
        if check_that_exists(families_db.families, {'project_id': destination_project_id}, not_more_than_one=False):
            result = update(families_db.families, {'project_id': destination_project_id}, {'project_id': destination_project_id+'_previous', 'version': datestamp})

        result = update(projects_db.projects, {'project_id': from_project_id},        {'project_id': destination_project_id, 'version': '2'})
        result = update(families_db.families, {'project_id': from_project_id},        {'project_id': destination_project_id, 'version': '2'})

        print("==========")
        print("Checking Projects:")
        if not check_that_exists(projects_db.projects, {'project_id': destination_project_id}, not_more_than_one=True):
            raise ValueError("After: There needs to be 1 project db in %(destination_project_id)s" % locals())
        if not check_that_exists(families_db.families, {'project_id': destination_project_id}, not_more_than_one=False):
            raise ValueError("After: There needs to be atleast 1 family db in %(destination_project_id)s" % locals())

        update_family_analysis_status(destination_project_id)
        
        print("Data transfer finished.")
        i = raw_input("Delete the 'from' project: %s? [Y/n] " % from_project_id)
        if i.strip() == 'Y':
            sample_management.delete_project(from_project_id)
            print("Project %s deleted" % from_project_id)
        else:
            print("Project not deleted")

    def handle(self, *args, **options):
        from_project_id = options["from_project"]
        destination_project_id = options["destination_project"]
        assert from_project_id
        assert destination_project_id

        print("Transfering data from project %s to %s" % (from_project_id, destination_project_id))
        print("WARNING: this can only be done once")
        if raw_input("Continue? [Y/n] ").lower() != 'y':
            return
        else:
            print("")

        self.transfer_project(from_project_id, destination_project_id)

        #for project in Project.objects.all():
        #    print("Project: " + project.project_id)
        #    update_family_analysis_status(project.project_id)
