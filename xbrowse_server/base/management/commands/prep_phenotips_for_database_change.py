from optparse import make_option
import sys
from django.core.management.base import BaseCommand
from xbrowse_server.phenotips.utilities import find_db_files
from xbrowse_server.phenotips.utilities import find_references
import os

'''
 Please note: this is a beta version of this tool and under development
'''

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--installation_dir',
                    '-d',
                    dest='ins_dir',
                    help='The PhenoTips installation directory.'
                    ), 
        make_option('--temporary_dir',
                    '-t',
                    dest='temp_dir',
                    help='A directory to keep temporary files in.'
                    ),                                                                                  
    )

    def handle(self, *args, **options):
      '''
        This is a helper script that is required to be run when changing the backend 
        DB between HSQLDB/Postgresql etc
      '''
      
      if options['ins_dir'] is None or options['temp_dir'] is None:
        self.print_help()
        sys.exit()
        
      if not os.path.exists(options['ins_dir']):
        print '\n\nError: directory does not exist: please enter a valid PhenoTips installation directory (--installation_dir).'
        sys.exit()
      
      if not os.path.exists(options['temp_dir']):
        print '\n\nError: directory does not exist: please enter a valid temporary directory (--temporary_dir).'
        sys.exit()
        
      
      self.start(options['ins_dir'], options['temp_dir'])
      
      
    def start(self,install_dir,temp_dir):
      '''
        Start the application.
      '''
      files_to_adjust=find_db_files(install_dir)
      find_references(files_to_adjust,temp_dir)
      
      
    def print_help(self):
      '''
        Help message
      '''
      print '\n\nPrepared backend of PhenoTips for database technology change.\n'
      print 'Requires:\n'
      print '1.Valid PhenoTips installation directory'
      print '2.Valid temporary file directory'
      print '\n\n'

      

