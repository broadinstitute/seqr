import itertools

from xbrowse import Family, Individual
from xbrowse.utils.basic_utils import slugify


def get_individuals_from_fam_file(fam_file, project_id='.'):
    """
    Returns a list of individuals from a FAM file
    """
    individuals = []

    for line in fam_file:
        try:
            # ignore these rows
            if line == '' or line.startswith('#'): continue

            fields = line.strip('\n').split('\t')

            indiv_id = slugify(fields[1], separator='_', replace_dot=True)
            family_id = slugify(fields[0], separator='_', replace_dot=True)

            paternal_id = slugify(fields[2], separator='_', replace_dot=True)
            if paternal_id == "0": paternal_id = "."

            maternal_id = slugify(fields[3], separator='_', replace_dot=True)
            if maternal_id == "0": maternal_id = "."

            gender = 'unknown'
            if fields[4] == '2' or fields[4].upper().startswith('F'):
                gender = 'female'
            elif fields[4] == '1' or fields[4].upper().startswith('M'):
                gender = 'male'

            affected_status = 'unknown'
            if fields[5] == '2' or fields[5].upper().startswith('A'):
                affected_status = 'affected'
            elif fields[5] == '1' or fields[5].upper().startswith('U'):
                affected_status = 'unaffected'
        except Exception as e:
            raise ValueError("Couldn't parse line: %(line)s. Fields: %(fields)s. exception: %(e)s" % locals())

        indiv = Individual(
            indiv_id,
            project_id=project_id,
            family_id=family_id,
            paternal_id=paternal_id,
            maternal_id=maternal_id,
            gender=gender,
            affected_status=affected_status,
        )
        individuals.append(indiv)

    return individuals


def validate_fam_file(fam_file):
    """
    Reads in and does basic consistency checks on the given fam file.

    Args:
        fam_file: An open fam file id
    """

    individuals = get_individuals_from_fam_file(fam_file)

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



def get_families_from_individuals(individuals, project_id='.'):
    """
    List of families from a set of individuals (matched by family_id)
    """
    sorted_individuals = sorted(individuals, key=lambda x: x.family_id)
    families = []
    for family_id, indivs in itertools.groupby(sorted_individuals, key=lambda x: x.family_id):
        family = Family(family_id, list(indivs), project_id=project_id)
        families.append(family)
    return families

def get_individuals_and_families_from_fam_file(fam_file, project_id='.'):
    """
    (individuals, families) tuple from fam file
    """
    individuals = get_individuals_from_fam_file(open(fam_file), project_id)
    return individuals, get_families_from_individuals(individuals, project_id)


def write_individuals_to_ped_file(fam_file, individuals):
    """
    Writes a set of individuals to a fam file.
    """
    if not individuals:
        return

    gender_map = {"M": "1", "F": "2", "U": "unknown"}
    affected_map = {"A": "2", "N": "1", "U": "unknown"}

    fam_file.write("# project id: %s\n" % individuals[0].project.project_id)
    fam_file.write("# %s\n" % "\t".join(["family", "individual", "paternal_id", "maternal_id", "gender", "affected"]))
    for i in sorted(individuals, key=lambda i: i.family_id):
        family_id = i.family.family_id if i.family else "unknown"
        gender = gender_map[i.gender]
        affected = affected_map[i.affected]
        fields = [family_id, i.indiv_id, i.paternal_id or ".", i.maternal_id or ".", gender, affected]
        fam_file.write("\t".join(fields) + "\n")

