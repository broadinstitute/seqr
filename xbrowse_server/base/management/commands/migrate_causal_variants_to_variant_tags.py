from collections import defaultdict
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Family, ProjectTag, VariantTag, CausalVariant
import random

def get_or_create_project_tag(project, new_tag_name="Causal Variant", description="causal variant", keywords=["causal"], color='#1f78b4'):
    """
    Gets or creates a particular ProjectTag in a given project.

    Args:
        project: The project that contains this tag
        new_tag_name: The name of the new tag (can contain spaces)
        keyword: A keyword used to check whether the project already contains the needed tag.

    Returns:
        new ProjectTag model object (or an existing one if a match was found)
    """
    for project_tag in ProjectTag.objects.filter(project=project):
        tag_name = project_tag.tag

        if not any([keyword.lower() in tag_name.lower() for keyword in keywords]):
            continue  # this isn't the tag we're looking for

        if tag_name.lower() == new_tag_name.lower():
            print("project %s: using tag: %s" % (project.project_id, tag_name))
            project_tag.tag=new_tag_name
            #project_tag.title=description
            project_tag.color=color
            project_tag.save()

            return project_tag

        # get user input on whether this tag should be use as the causal variant tag
        while True:
            i = raw_input(project.project_id + " use tag: " + tag_name + "? [y/n] ")
            if i == "y":
                project_tag.tag=new_tag_name
                #project_tag.title=description
                project_tag.color=color
                project_tag.save()

                return project_tag
            elif i == "n":
                break

    print("project %s: Creating %s - %s tag" % (project.project_id, new_tag_name, description))
    new_project_tag = ProjectTag.objects.create(project=project, tag=new_tag_name, title=description, color=color)
    return new_project_tag


class Command(BaseCommand):
    """Copy CausalVariants to VariantTags"""

    def handle(self, *args, **options):

        counter = defaultdict(int)

        for project in Project.objects.all():
            print("project %s: Looking at tags: %s" % (project.project_id, ", ".join([t.tag for t in ProjectTag.objects.filter(project=project)])))

            counter['projects'] += 1

            # make sure none of the existing tags have the same color as the tags about to be created
            for project_tag in ProjectTag.objects.filter(project=project):
                if project_tag.color in ['#33a02c', '#ff0000', '#ffbf00', '#1f78b4']:
                    project_tag.color = random.choice(
                        list(
                            set(['#a6cee3', '#b2df8a', '#fdbf6f', '#cab2d6', '#6a3d9a', '#8F754F', '#383838']) -
                            set([t.color for t in ProjectTag.objects.filter(project=project)])))
                    project_tag.save()

            # create the new ProjectTags
            #get_or_create_project_tag(project, new_tag_name="Strong Candidate", description="plausible candidate gene or variant",
            #                          keywords=["good", "strong"], color='#33a02c')
            #get_or_create_project_tag(project, new_tag_name="Excluded Variant", description="variant considered but excluded",
            #                          keywords=["exclude"], color='#ff0000')
            #get_or_create_project_tag(project, new_tag_name="Review", description="variant looks interesting but requires additional review at gene and variant level",
            #                          keywords=["review"], color='#ffbf00')

            causal_variant_tag = get_or_create_project_tag(project, new_tag_name="Causal Variant", description="causal variant", keywords=["causal"], color='#1f78b4' )
            
            # create a VariantTag for each CausalVariant record
            for causal_variant in CausalVariant.objects.all():
                if causal_variant.family.project != project:
                    continue
                variant_tag, created = VariantTag.objects.get_or_create(project_tag=causal_variant_tag,
                                                                        family=causal_variant.family,
                                                                        xpos=causal_variant.xpos,
                                                                        ref=causal_variant.ref,
                                                                        alt=causal_variant.alt)

                if created:
                    counter['created variant_tags'] += 1
                    print("project %s: Tagged a causal variant: %s" % (project.project_id, variant_tag.toJSON()))

        print("Stats:")
        for k, v in counter.items():
            print("%s %s" % (v, k))
