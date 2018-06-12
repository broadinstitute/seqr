from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.management.base import BaseCommand
from pprint import pprint, pformat
import xlrd
import re
from django.contrib.auth.models import User

from seqr.views.apis.phenotips_api import get_patient_data, update_patient_data
from xbrowse_server.base.models import Family, Individual, ProjectTag, VariantTag
from seqr.models import Project as SeqrProject
from xbrowse import genomeloc
from django.db.models import Q

printed_project = {}

def add_initial_omim_and_coded_phenotype(row):
    try:
        family = Family.objects.get(project__project_id__iexact=row["Project"], family_id__iexact=row["Family Id"])
    except Exception as e:
        print("ERROR: couldn't find family: '%s' '%s'" % (row["Project"], row["Family Id"]))
        return

    seqr_project = SeqrProject.objects.get(deprecated_project_id__iexact=row["Project"])

    if seqr_project.deprecated_project_id not in printed_project:
        print("=========")
        print("Processing " + str(seqr_project.deprecated_project_id))
        printed_project[seqr_project.deprecated_project_id] = True


    if family.coded_phenotype != row['Coded Phenotype']:
        family.coded_phenotype = row['Coded Phenotype']
        print("Setting %s coded phenotype to %s" % (family, family.coded_phenotype))
        family.save()

    omim_number = row['Initial OMIM']
    if not omim_number:
        return

    individuals = Individual.objects.filter(family=family, affected='A')
    if len(individuals) == 0:
        print("ERROR: No affected individuals found in family: " + str(family))
        return

    for individual in individuals:
        try:
            patient_data = get_patient_data(seqr_project, individual.phenotips_id, is_external_id=True)
            if omim_number not in patient_data.get('disorders', [{}])[0].get('id', ''):
                patient_data['disorders'] = [{ 'id': 'MIM:'+omim_number }]
                print("updating disorder to %s in %s: %s" % (omim_number, individual, "") )#pformat(patient_data)))
                update_patient_data(seqr_project, individual, patient_data)
        except Exception as e:
            print("Couldn't access phenotips for %s %s: %s" % (family.project, individual, e))


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('coded_phenotype_file')

    def handle(self, *args, **options):
        xls_file = options.get("coded_phenotype_file")

        print("Reading " + xls_file)

        print("==============")
        for worksheet_i in range(0, 5):
            rows = parse_xls(xls_file, worksheet_index=worksheet_i)  # OMIM #s - Initial
            for i, row in enumerate(rows):
                add_initial_omim_and_coded_phenotype(row)


def parse_xls(path, worksheet_index=0):

    wb = xlrd.open_workbook(file_contents=open(path).read())

    ws = wb.sheet_by_index(worksheet_index)
    print("Parsing worksheet: %s" % (ws.name, ))

    header = []
    rows = []
    for i in range(ws.nrows):
        row_fields = [ws.cell(rowx=i, colx=j).value for j in range(ws.ncols)]
        if i == 0 and _is_header_row("\t".join(row_fields)):
            header = row_fields
            continue
        elif not header:
            raise ValueError("Header row not found")

        parsed_row = []
        for j in range(ws.ncols):
            cell = ws.cell(rowx=i, colx=j)
            cell_value = cell.value
            if not cell_value:
                # if the 1st and 2nd column in a row is empty, treat this as the end of the table
                if j == 0 and (ws.ncols < 2 or not ws.cell(rowx=i, colx=1).value):
                    break
                else:
                    parsed_row.append('')
            else:
                if cell.ctype in (2,3) and int(cell_value) == cell_value:
                    cell_value = int(cell_value)
                parsed_row.append(unicode(cell_value).encode('UTF-8'))
        else:
            # keep this row as part of the table
            if len(parsed_row) != len(header):
                raise ValueError("Row %s contains %d columns, while header contains %s: %s" % (
                    i, len(parsed_row), len(header), parsed_row))

            row_dict = dict(zip(header, parsed_row))
            rows.append(row_dict)

    return rows


def _is_header_row(header_row):
    #print("Header row: " + header_row)
    return True
