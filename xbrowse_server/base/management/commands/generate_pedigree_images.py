"""This command takes a project id and, for each family, tried to auto-generate a pedigree plot by 
1. Writing out a slightly-specialized .ped file for just this family
2. Running the HaploPainter1.043.pl tool on this .ped file to generate a .png image
3. If the pedigree image was generated successfully, set this image as the family.pedigree_image file. 
4. Delete the .ped file and other temp files. 
""" 

from django.core.management.base import BaseCommand
from django.core.files import File

from xbrowse_server.base.models import Project, Individual

from optparse import make_option
import os



def run(s):
    #print(s)
    os.system(s)

placeholder_indiv_counter = 0

def create_placeholder_indiv(family, gender):
    """Utility function for creating an individual for whom data is not available.
    Args:
        gender: 'M' or 'F'
    Returns:
        Individual model instance 
    """
    global placeholder_indiv_counter
    assert gender in ('M', 'F'), "Unexpected gender value: '%s'" % str(gender)

    placeholder_indiv_counter += 1

    i = Individual()
    i.indiv_id = 'dummy_%d' % placeholder_indiv_counter  # fake indiv id
    i.family = family
    i.gender = gender
    i.paternal_id = ''
    i.maternal_id == ''
    i.affected = 'INVISIBLE'  # use a special value to tell HaploPainter that this indiv should be drawn as '?'

    return i


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('-f', '--force', action="store_true", help="Replace any existing pedigree images")

    def handle(self, *args, **options):
        force = options.get('force')
        for project_name in args:
            project = Project.objects.get(project_id=project_name)
            individuals = project.get_individuals()
            filename = project.project_id + ".ped"
            print("Writing %s individuals to %s" % (len(individuals), filename))

        for project_name in args:
            project = Project.objects.get(project_id=project_name)
            print(project_name)
            for family in project.get_families():
                if len(family.get_individuals()) < 2:
                    continue
            
                print("Processing %s" % (family,))
                family_id = family.family_id
                
                parents_ids_to_placeholder_spouse = {}   # when only one parent specified, maps indiv id to placeholder parent
                individuals_in_family = []
                family_has_parents = False  # used to check if this family is only siblings (or only 1 individual)
                for i in family.get_individuals():
                    if i.paternal_id == '.':
                        i.paternal_id = ''

                    if i.maternal_id == '.':
                        i.maternal_id = ''

                    if i.maternal_id or i.paternal_id:
                        family_has_parents = True

                    # HaploPainter1.043.pl doesn't support families with only 1 parent, so add dummy individuals
                    if bool(i.paternal_id == '') ^ bool(i.maternal_id == ''):
                        if i.paternal_id == '':
                            if i.maternal_id in parents_ids_to_placeholder_spouse:
                                parent_i = parents_ids_to_placeholder_spouse[i.maternal_id]
                            else:
                                parent_i = create_placeholder_indiv(family, 'M')
                                parents_ids_to_placeholder_spouse[i.maternal_id] = parent_i  # save placeholder father
                                individuals_in_family.append(parent_i)
                            i.paternal_id = parent_i.indiv_id
                        elif i.maternal_id == '':
                            if i.paternal_id in parents_ids_to_placeholder_spouse:
                                parent_i = parents_ids_to_placeholder_spouse[i.paternal_id]
                            else:
                                parent_i = create_placeholder_indiv(family, 'F')     # create placeholder mother                   
                                parents_ids_to_placeholder_spouse[i.paternal_id] = parent_i  
                                individuals_in_family.append(parent_i)
                            i.maternal_id = parent_i.indiv_id
                        else:
                            raise Exception("Unexpected logical state")
                        
                        individuals_in_family.append(i)
                    else:
                        individuals_in_family.append(i)

                if not family_has_parents:
                    mother = create_placeholder_indiv(family, 'F')
                    father = create_placeholder_indiv(family, 'M')
                    for i in individuals_in_family:
                        i.maternal_id = mother.indiv_id
                        i.paternal_id = father.indiv_id
                    individuals_in_family.append(mother)
                    individuals_in_family.append(father)

                with open(family_id + ".ped", "w") as f:
                    gender_map = {"M": "1", "F": "2", "U": "0"}
                    # HaploPainter1.043.pl has been modified to hide individuals with affected-status='9'
                    affected_map = {"A": "2", "N": "1", "U": "0", "INVISIBLE": "9"} 
                
                    f.write("# %s\n" % "\t".join(["family", "individual", "paternal_id", "maternal_id", "gender", "affected"]))
                    for i in individuals_in_family:
                        family_id = i.family.family_id if i.family else "unknown"
                        gender = gender_map[i.gender]
                        affected = affected_map[i.affected]
                        fields = [family_id, i.indiv_id, i.paternal_id or '0', i.maternal_id or '0', gender, affected]
                        #print(fields)
                        f.write("\t".join(fields) + "\n")
                    
                haplopainter_path = os.path.dirname(__file__) + '/HaploPainter1.043.pl'
                run("/usr/bin/perl %(haplopainter_path)s -b -pedfile %(family_id)s.ped -outformat png -family %(family_id)s -outfile %(family_id)s.png" % locals() )

                if not os.path.isfile(family_id+'.png'):
                    for i in individuals_in_family:
                        print("Individual %s" % [('family_id', i.family), ('indiv_id', i.indiv_id), ('paternal_id', i.paternal_id), ('maternal_id', i.maternal_id), ('gender', i.gender), ('affected', i.affected)])
                    print('------------')
                    continue   # failed to generate image
                        
                if family.pedigree_image and not force:
                    print("Pedigree image already exists. Skipping..")
                else:
                    family.pedigree_image.save(family_id+'.png', File(open(family_id+'.png')))
                    family.save()

                run("rm %(family_id)s.ped" % locals())
                run("rm %(family_id)s.png" % locals())

            print("\nFinished")

