from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
import sys
from xbrowse_server.phenotips.utilities import add_new_user_to_phenotips
from xbrowse_server.phenotips.utilities import get_uname_pwd_for_project
from django.conf import settings

class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args)<2 or not args[0] or not args[1]:
          print '\n'
          print 'please provide a project ID and a project name as the first two arguments. If project name as spaces, please remember to enclose in double quotes'
          print 'example: python manage.py 1kg "1000 Genomes Project"\n'
          sys.exit()
        project_id = args[0]
        project_name = args[1]
        if "." in project_id:
            sys.exit("ERROR: A '.' in the project ID is not supported")

        if Project.objects.filter(project_id=project_id).exists():
            #raise Exception("Project exists :(")
            print '\nsorry, I am unable to create that project since it exists already\n'
            sys.exit()
        Project.objects.create(project_id=project_id)
        self.__create_user_in_phenotips(project_id,project_name)
      
    #create a username that represents this project in phenotips  
    def __create_user_in_phenotips(self,project_id,project_name):
      uname,pwd=get_uname_pwd_for_project(project_id)
      #first create a user with full write privileges
      add_new_user_to_phenotips(project_name,
                                project_name, 
                                uname,
                                settings.PHENOPTIPS_ALERT_CONTACT ,
                                pwd)
      #next create a user with ONLY VIEW privileges (the rights are determined when pateints are added in,
      #this step merely creates the user
      add_new_user_to_phenotips(project_name + '(view only)',
                                project_name + '(view only)', 
                                uname+'_view',
                                settings.PHENOPTIPS_ALERT_CONTACT ,
                                pwd)
