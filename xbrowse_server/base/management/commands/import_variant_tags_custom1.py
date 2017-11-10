from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.management.base import BaseCommand
import xlrd

from seqr.models import Family


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('variant_tag_file')

    def handle(self, *args, **options):
        xls_file = options.get("variant_tag_file")

        print("Reading " + xls_file)

        print("==============")
        rows = parse_xls(xls_file, worksheet_index=0)  # Tier 1 tags
        for i, row in enumerate(rows):
            if row["New Tag"] == row["Current Tag"]:
                #print("Skipping row %s: tags are the same" % i)
                continue

        print(rows[i])

        print("==============")
        rows = parse_xls(xls_file, worksheet_index=1)  # Tier 2 tags
        for i, row in enumerate(rows):
            if row["New Tag"] == row["Current Tag"]:
                #print("Skipping row %s: tags are the same" % i)
                continue
        print(rows[i])

        print("==============")
        rows = parse_xls(xls_file, worksheet_index=2)  # OMIM #s - Initial
        for i, row in enumerate(rows):
            family_id = row["CMG Internal Project ID(s)"].strip()
            try:
                family = Family.objects.get(family_id=family_id)
            except ObjectDoesNotExist as e:
                if "_" in family_id:
                    family_id = "_".join(family_id.split("_")[1:])
                    family_id = family_id.split(".")[0]
                try:
                    family = Family.objects.get(family_id=family_id)
                except ObjectDoesNotExist as e:
                    print("Family not found: " + str(family_id))
                except MultipleObjectsReturned as e:
                    pass
            except MultipleObjectsReturned as e:
                pass

        print("==============")
        rows = parse_xls(xls_file, worksheet_index=3)  # OMIM#s - Post Discovery
        for i, row in enumerate(rows):
            family_id = row["Family ID (CollPrefix_ID)"].strip()
            try:
                family = Family.objects.get(family_id=family_id)
            except ObjectDoesNotExist as e:
                if "_" in family_id:
                    family_id = "_".join(family_id.split("_")[1:])
                    family_id = family_id.split(".")[0]
                try:
                    family = Family.objects.get(family_id=family_id)
                except ObjectDoesNotExist as e:
                    print("Family not found: " + str(family_id))
                except MultipleObjectsReturned as e:
                    pass
            except MultipleObjectsReturned as e:
                pass

        print("==============")
        rows = parse_xls(xls_file, worksheet_index=4)  # Coded Phenotype
        for i, row in enumerate(rows):
            family_id = row["Family ID (CollPrefix_ID)"].strip()
            try:
                family = Family.objects.get(family_id=family_id)
            except ObjectDoesNotExist as e:
                if "_" in family_id:
                    family_id = "_".join(family_id.split("_")[1:])
                    family_id = family_id.split(".")[0]
                try:
                    family = Family.objects.get(family_id=family_id)
                except ObjectDoesNotExist as e:
                    print("Family not found: " + str(family_id))
                except MultipleObjectsReturned as e:
                    pass
            except MultipleObjectsReturned as e:
                pass

        print(rows[i])


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