"""This command takes a project id and, for each family, tried to auto-generate a pedigree plot by 
1. Writing out a slightly-specialized .ped file for just this family
2. Running the HaploPainter1.043.pl tool on this .ped file to generate a .png image
3. If the pedigree image was generated successfully, set this image as the family.pedigree_image file. 
4. Delete the .ped file and other temp files. 
""" 

from django.core.management.base import BaseCommand
from django.core.files import File

from xbrowse_server.base.models import Project, Family, Individual

from optparse import make_option
import os
import settings


def run(s):
    print(s)
    os.system(s)

def _encode_id(id_string):
    id_string = ''.join([i if ord(i) < 128 else ' ' for i in id_string])
    return id_string.replace('?', '').replace(' ', '')

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
        parser.add_argument('project_id', nargs='?')
        parser.add_argument('family_id', nargs="*")
        parser.add_argument('-f', '--force', action="store_true", help="Replace any existing pedigree images")
        parser.add_argument('--all', action="store_true", help="Generate pedigree images for all families that don't have them")

    def handle(self, *args, **options):
        force = options.get('force')

        if options.get('all'):
            projects = Project.objects.all()
        else:
            project_id = options.get('project_id')
            projects = [Project.objects.get(project_id=project_id)]
            

        for project in projects:
            print("=============================")
            print("     Project: " + str(project))
            print("=============================")

            individuals = project.get_individuals()
            if options.get('family_id', None):
                families = Family.objects.filter(project__project_id = project_id, family_id__in=options.get('family_id') )
            else:
                families = project.get_families() 
        
            for family in families:
                if len(family.get_individuals()) < 2:
                    continue

                if family.pedigree_image and os.path.isfile(os.path.abspath(os.path.join(settings.MEDIA_ROOT, family.pedigree_image.name))) and not force:
                    print("Pedigree image already exists. Skipping..")
                    continue
                
                print("Processing %s" % (family,))
                family_id = _encode_id(family.family_id)
                
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
                            i.paternal_id = parent_i.nickname or parent_i.indiv_id 
                        elif i.maternal_id == '':
                            if i.paternal_id in parents_ids_to_placeholder_spouse:
                                parent_i = parents_ids_to_placeholder_spouse[i.paternal_id]
                            else:
                                parent_i = create_placeholder_indiv(family, 'F')     # create placeholder mother                   
                                parents_ids_to_placeholder_spouse[i.paternal_id] = parent_i  
                                individuals_in_family.append(parent_i)
                            i.maternal_id =  parent_i.nickname or parent_i.indiv_id
                        else:
                            raise Exception("Unexpected logical state")
                        
                        individuals_in_family.append(i)
                    else:
                        individuals_in_family.append(i)

                if not family_has_parents:
                    mother = create_placeholder_indiv(family, 'F')
                    father = create_placeholder_indiv(family, 'M')
                    for i in individuals_in_family:
                        i.maternal_id = mother.nickname or mother.indiv_id 
                        i.paternal_id = father.nickname or father.indiv_id
                    individuals_in_family.append(mother)
                    individuals_in_family.append(father)

                
                output_ped_filename = family_id + ".ped"
                print("Writing temp ped file to: " +  os.path.abspath(output_ped_filename))
                with open(output_ped_filename, "w") as f:
                    gender_map = {"M": "1", "F": "2", "U": "0"}
                    # HaploPainter1.043.pl has been modified to hide individuals with affected-status='9'
                    affected_map = {"A": "2", "N": "1", "U": "0", "INVISIBLE": "9"} 
                
                    f.write("# %s\n" % "\t".join(["family", "individual", "paternal_id", "maternal_id", "gender", "affected"]))
                    for i in individuals_in_family:
                        family_id = _encode_id(i.family.family_id if i.family else "unknown")
                        gender = gender_map[i.gender]
                        affected = affected_map[i.affected]
                        fields = map(_encode_id, [family_id, i.nickname or i.indiv_id, i.paternal_id or '0', i.maternal_id or '0', gender, affected])
                        #print(fields)
                        f.write("\t".join([field for field in fields]) + "\n")
                    
                haplopainter_path = os.path.dirname(__file__) + '/HaploPainter1.043.pl'
                run("perl %(haplopainter_path)s -b -pedfile %(family_id)s.ped -outformat png -family %(family_id)s -outfile %(family_id)s.png" % locals() )

                if not os.path.isfile(family_id+'.png'):
                    for i in individuals_in_family:
                        print("Individual %s" % [('family_id', i.family), ('indiv_id', i.indiv_id), ('paternal_id', i.paternal_id), ('maternal_id', i.maternal_id), ('gender', i.gender), ('affected', i.affected)])
                    print('------------')
                    family.pedigree_image = None
                    family.save()
                    continue   # failed to generate image
                        
                    
                family.pedigree_image.save(family_id+'.png', File(open(family_id+'.png')))
                print("saving", os.path.abspath(os.path.join(settings.MEDIA_ROOT, family.pedigree_image.name)))
                family.save()
                    
                #seqr_project = SeqrProject.objects.filter(deprecated_project_id=project_id)[0]
                #seqr_family = SeqrFamily.objects.filter(project=seqr_project, family_id=family_id)[0]
                #seqr_family.pedigree_image.save(family_id+'.png', File(open(family_id+'.png')))
                #print("saving seqr pedigree ", os.path.abspath(os.path.join(settings.MEDIA_ROOT, seqr_family.pedigree_image.name)))
                #seqr_family.save()

                run("rm %(family_id)s.ped" % locals())
                run("rm %(family_id)s.png" % locals())

        print("\nFinished")

