import itertools
import slugify

from xbrowse import Family, Individual
        
def get_individuals_from_fam_file(fam_file, project_id='.'):
    """
    Returns a list of individuals from a FAM file
    """
    individuals = []

    for line in fam_file:

        # ignore these rows
        if line == '' or line.startswith('#'): continue

        fields = line.strip('\n').split('\t')

        indiv_id = slugify.slugify(fields[1])
        family_id = slugify.slugify(fields[0])

        paternal_id = slugify.slugify(fields[2])
        if paternal_id == "0": paternal_id = "."

        maternal_id = slugify.slugify(fields[3])
        if maternal_id == "0": maternal_id = "."

        gender = 'unknown'
        if fields[4] == '2':
            gender = 'female'
        elif fields[4] == '1':
            gender = 'male'

        affected_status = 'unknown'
        if fields[5] == '2':
            affected_status = 'affected'
        elif fields[5] == '1':
            affected_status = 'unaffected'

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
        fields = [family_id, i.indiv_id, i.paternal_id, i.maternal_id, gender, affected]
        fam_file.write("\t".join(fields) + "\n")


