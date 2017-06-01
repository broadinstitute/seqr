"""
APIs used to process requests for modifying family and individual metadata
"""

import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from openpyxl import load_workbook

from seqr.models import Individual, Family
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_to_orm_utils import update_individual_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.request_utils import _get_project_and_check_permissions

logger = logging.getLogger(__name__)


def parse_ped_file(file_obj):
    result = []
    for line in file_obj:
        if not line or line.startswith('#'):
            continue
        fields = line.rstrip('\n').split('\t')
        result.append(fields)
    return result


def process_rows(rows):
    result = []
    for row in rows:
        fields = row

        if len(fields) < 6:
            raise ValueError("Invalid")

        family_id = fields[0]
        if not family_id:
            raise ValueError("Invalid")

        individual_id = fields[1]
        if not individual_id:
            raise ValueError("Invalid")

        paternal_id = fields[2]
        if paternal_id == ".":
            paternal_id = ""

        maternal_id = fields[3]
        if maternal_id == ".":
            maternal_id = ""

        sex = fields[4]
        if sex == '1' or sex.upper().startswith('M'):
            sex = 'M'
        elif  sex == '2' or sex.upper().startswith('F'):
            sex = 'F'
        elif not sex:
            sex = 'U'
        else:
            raise ValueError("Invalid")

        affected = fields[5]
        if affected == '1' or affected.upper().startswith('U'):
            affected = 'N'
        elif affected == '2' or affected.upper().startswith('A'):
            affected = 'A'
        elif not affected:
            affected = 'U'
        elif affected:
            raise ValueError("Invalid")

        notes = fields[6] if len(fields) > 6 else None
        hpo_terms = fields[7] if len(fields) > 7 else None
        result.append({
            'familyId': family_id,   # unknown
            'individualId': individual_id,
            'paternalId': paternal_id,
            'maternalId': maternal_id,
            'sex': sex,
            'affected': affected,
            'notes': notes,
            'hpoTerms': hpo_terms # unknown
        })

    return result


def parse_xls(stream):
    wb = load_workbook(stream, data_only=True)
    ws = wb.active
    rows = []
    for i, row in enumerate(ws.rows):
        if i == 0:
            logger.info("Skipping header row: " + str(row))
            continue
        parse_row = []
        for j, cell in enumerate(row):
            if cell.value is None:
                if j == 0:
                    break
                parse_row.append('')
            else:
                parse_row.append(str(cell.value))
        else:
            rows.append(parse_row)

    return rows



def validate_individual_records(records):
    return


def validate_fam_file(fam_file):
    """
    Reads in and does basic consistency checks on the given fam file.

    Args:
        fam_file: An open fam file id
    """

    individuals = parse_ped_file(fam_file)

    # used for validating
    indiv_to_sex = {}
    indiv_to_pat_id = {}
    indiv_to_mat_id = {}
    indiv_to_family_id = {}
    for i in individuals:
        indiv_id = i.indiv_id
        #assert i.indiv_id not in indiv_to_family_id, "duplicate individual_id: %(indiv_id)s" % locals()

        indiv_to_family_id[indiv_id] = i.family_id
        if i.maternal_id and i.maternal_id != '.':
            indiv_to_mat_id[indiv_id] = i.maternal_id
        if i.paternal_id and i.paternal_id != '.':
            indiv_to_pat_id[indiv_id] = i.paternal_id
        indiv_to_sex[indiv_id] = i.gender

    print("Validating %d individuals in %d families" % (len(indiv_to_family_id), len(set(indiv_to_family_id.values()))))


    # run basic consistency checks
    errors = []
    for indiv_id, family_id in indiv_to_family_id.items():

        for label, indiv_to_parent_id_map in (('maternal', indiv_to_mat_id), ('paternal', indiv_to_pat_id)):
            if indiv_id not in indiv_to_parent_id_map:
                # parent not specified
                continue

            parent_id = indiv_to_parent_id_map[indiv_id]
            if parent_id not in indiv_to_sex:
                print("WARNING: %(indiv_id)s's %(label)s id: %(parent_id)s not found among individual ids: %(indiv_to_family_id)s" % locals())
                continue

            parent_sex = indiv_to_sex[parent_id]
            if (label=='maternal' and parent_sex == 'male') or (label=='paternal' and parent_sex == 'female'):
                errors.append("ERROR: %(parent_id)s is marked as %(label)s for %(indiv_id)s but has sex == %(parent_sex)s" % locals())

            parent_family_id = indiv_to_family_id[parent_id]
            if parent_family_id != family_id:
                errors.append("%(indiv_id)s's family id: %(family_id)s does't match %(label)s family id: %(parent_family_id)s" % locals())
    if errors:
        raise ValueError("\n" + "\n".join(map(str, errors)))



@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def receive_families_and_individuals_table(request, project_guid):
    """Process table.

    Args:
        project_guid (string): GUID of the family.
    """

    project = _get_project_and_check_permissions(project_guid, request.user)

    for stream in request.FILES.values():
        filename = stream._name
        file_size = stream._size
        content_type = stream.content_type
        content_type_extra = stream.content_type_extra

        #print(filename, file_size, content_type, content_type_extra)

        if filename.endswith('.ped') or filename.endswith('tsv'):
            rows = parse_ped_file(stream)
        elif filename.endswith('.xls') or filename.endswith('.xlsx'):
            rows = parse_xls(stream)
        else:
            raise ValueError("Invalid")

        records = process_rows(rows)
        validate_individual_records(records)
        for record in records:
            family, created = Family.objects.get_or_create(project=project, family_id=record['familyId'])
            if created:
                logger.info("Created family: %s" % str(family))

            individual, created = Individual.objects.get_or_create(family=family, individual_id=record['individualId'])
            if created:
                logger.info("Created individual: %s" % str(individual))

            update_individual_from_json(individual, record, allow_unknown_keys=True)

    return create_json_response({})


    # with open('some/file/name.txt', 'wb+') as destination:
        #for line in value:
        #    print(line)
        #for chunk in value.chunks():
            #destination.write(chunk)
        #    print(chunk)

    #@print("REQUEST FILES", request.FILES)
    #print("REQUEST", request)

