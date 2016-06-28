import gzip
import sys
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
from xbrowse_server import sample_management
from xbrowse.parsers import fam_stuff
from xbrowse.utils import slugify


try:
    from openpyxl import load_workbook
except ImportError:
    print("WARNING: Couldn't import openpyxl. --xls option will not work")


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--xls',
                    help=('An Excel spreadsheet with the following columns: '
                          'Collaborator Family ID, Collaborator Sample ID, Collaborator Father Sample ID, '
                          'Collaborator Mother Sample ID, Sex, Affected Status. '
                          'For example: ["NR", "NR_0", "NR_1", "NR_2", "Male", "Affected"]'), required=True)

        parser.add_argument('--ped', help='The output PED file', required=True)
        parser.add_argument('-d', '--dont-validate', help='Dont validate the file', action="store_true")

    def handle(self, *args, **options):
        xls_file = options.get('xls')
        title_row, xl_rows = parse_xl_workbook(xls_file)
        
        output_ped_filename = options.get('ped')        
        write_xl_rows_to_ped(output_ped_filename, xl_rows)
        if options.get('dont_validate'):
            pass
        else:
            fam_stuff.validate_fam_file(open(output_ped_filename))

def write_xl_rows_to_ped(ped_filename, xl_rows):
    """Writes the given rows to a ped file with the given filename

    Args:
        ped_filename: output filename 
        xl_rows: a list of tuples where each tuple has 6 elements: family_id, sample_id, paternal_id, maternal_id, sex, affected
    """

    with open(ped_filename, 'w') as out:
        for i, row in enumerate(xl_rows):
            assert len(row) >= 6, "Unexpected number of columns in row #%(i)s: %(row)s" % locals()

            if not any(row):  
                continue  # skip empty rows
            
            #for _id in filter(None, row[0:4]):
            #    assert slugify(_id) == _id, "row %(i)s has unexpected characters in id: '%(_id)s'. Only a-Z0-9 and - or _ are allowed" % locals()

            family_id, sample_id, paternal_id, maternal_id, sex, affected = row[0:6]


            assert family_id and sample_id, "family_id or sample_id not specified in row: %(row)s" % locals()

            paternal_id = '.' if paternal_id is None else paternal_id
            maternal_id = '.' if maternal_id is None else maternal_id

            if sex:
                sex = {'M': '1', 'F': '2'}[sex[0].upper()]
            else:
                sex ='.'
                
            if affected is not None:
                affected = {'unaffected': '1', 'no': '1', 'affected': '2', 'yes':'2'}[affected.strip().lower()]
            else:
                affected = '-9'

            out.write('\t'.join([family_id, sample_id, paternal_id, maternal_id, sex, affected]) + '\n')
                   

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
    print("Loading Excel file: %s" % xl_file_name)
    wb = load_workbook(filename=xl_file_name, data_only=True)
    ws = wb.active
    for i,row in enumerate(ws.rows):
        r=[]
        for cell in row:
            if cell.value is None:
                r.append('')
            else:
                r.append(str(cell.value))
        if has_title and i==0:
            title_row=(tuple(r))
        else:
            ped.append(tuple(r))
    return title_row, ped


def writef(t,handle):
    '''
      Write text to file
    '''
    handle.write(t.encode('utf8'))
