import gzip
import sys
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
from xbrowse_server import sample_management
from xbrowse.parsers import vcf_stuff
try:
    from openpyxl import load_workbook
except ImportError:
    print("WARNING: Couldn't import openpyxl. --xls option will not work")


class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('--sample-list',
                    dest='sample-list',
                    default=False,
                    help='A sample list to gather patient information from.')
        parser.add_argument('--vcf',
                    help='A VCF file to gather patient information from.'
                    )
        parser.add_argument('--ped',
                    help='A PED file to gather patient information from (PREFERRED due to richer information set).'
                    )
        parser.add_argument('--xls',
                    help=('An Excel spreadsheet with the following columns: '
                          'Collaborator Family ID, Collaborator Sample ID, Collaborator Father Sample ID, '
                          'Collaborator Mother Sample ID, Sex, Affected?')
                    )
        parser.add_argument('args', nargs='*')


    def handle(self, *args, **options):

        if len(args)==0 or options['vcf'] is None and options['ped'] is None:
          print '\n\nPlease enter a VCF file (--vcf), OR IDEALLY A PED file (--ped), and a project ID (first positional argument).'
          print 'For example: python manage.py add_individuals_to_project  myProjectId --ped myPed.ped\n'
          print 'If you also wish to create patients in phenotips, please use the --create_phenotips_patients\n'
          sys.exit()
          
        project_id = args[0]
        project = Project.objects.get(project_id=project_id)

        if options.get('sample_list'):
            indiv_id_list = []
            for line in open(options.get('sample_list')):
                if line.strip() == "" or line.startswith('#'):
                    continue
                indiv_id_list.append(line.strip())
            sample_management.add_indiv_ids_to_project(project, indiv_id_list)

        if options.get('vcf'):
            vcf_path = options.get('vcf')
            if vcf_path.endswith('.gz'):
                vcf = gzip.open(vcf_path)
            else:
                vcf = open(vcf_path)
            indiv_id_list = vcf_stuff.get_ids_from_vcf(vcf)
            sample_management.add_indiv_ids_to_project(project, indiv_id_list)


        if options.get('ped'):
            fam_file = open(options.get('ped'))
            individual_details = sample_management.update_project_from_fam(project, fam_file)
            for j in individual_details:
                print("Adding %s: %s" % (j['indiv_id'], j))

        if options.get('xls'):
            xls_file = options.get('xls')
            title_row, ped_rows = parse_xl_workbook(xls_file)
            print(ped_rows)
            temp_ped_filename = 'temp.ped'
            process_ped_rows(temp_ped_filename, ped_rows)
            individual_details = sample_management.update_project_from_fam(project, temp_ped_filename)
            for j in individual_details:
                print("Adding %s: %s" % (j['indiv_id'], j))
            #os.remove(temp_ped_filename)



def process_ped_rows(out_name,ped_rows):
    '''
    Process a PED and transform it into RDAP friendly format
    Inputs:
    1. A list of PED rows (each row is a tuple of ped columns)
    Outputs:
    1. True/False on success
    '''
    out=open(out_name,'w')

    for row in ped_rows:
        for i,col in enumerate(row):
            if i==0:
                writef(extract_family_id(col),out)
                writef('\t',out)
                writef(col.rstrip(),out),
            else:
                if col is not None:
                    adj=col
                    if i==3:
                        if col=='F':
                            adj='2'
                        if col=='M':
                            adj='1'
                    if i==4:
                        if col=='Unaffected':
                            adj='1'
                        if col=='Affected':
                            adj='2'
                    writef(adj,out)
                else:
                    if i==4:
                        print '----WARN: found a missing Affected/Unaffected status, designating as -9'
                        writef('-9',out)
                    else:
                        writef('.',out)
            if i<len(row)-1:
                writef('\t',out)
        writef('\n',out)
    out.close()
    return True


def extract_family_id(patient_id):
    '''
    Extract family ID from patient ID.
    Assumes patient ID looks like "MAN_0618_01_1"
    Inputs:
    1. A patient ID
    Outputs:
    2. The family ID
    '''
    return patient_id.split('-')[1]


def parse_xl_workbook(xl_file_name,has_title=True):
    '''
    Parse input workbook
    Input:
     1. An xcel file name

    Outputs:
     1. A tuple of column titles
     2. A list of rows. Each row
    '''
    ped=[]
    title_row=()
    wb = load_workbook(filename =xl_file_name)
    ws = wb.active
    for i,row in enumerate(ws.rows):
        r=[]
        for cell in row:
            r.append(cell.value)
        if has_title and i==0:
            title_row=(tuple(r))
        else:
            ped.append(tuple(r))
    return title_row,ped


def writef(t,handle):
    '''
      Write text to file
    '''
    handle.write(t.encode('utf8'))


