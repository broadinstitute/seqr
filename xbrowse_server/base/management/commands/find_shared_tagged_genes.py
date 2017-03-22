import os
from django.core.management.base import BaseCommand
from collections import defaultdict, namedtuple
from tqdm import tqdm
from xbrowse_server.base.models import Project, VariantTag, ProjectTag
from xbrowse_server.mall import get_datastore, get_reference
from xbrowse_server.gene_lists.models import GeneList

from reference_data.models import OMIM

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        #genomicFeatures section
        self.all_gene_lists = defaultdict(set)
        self.gene_to_gene_lists = defaultdict(set)
        for gene_list in GeneList.objects.all():
            print('gene list: [%s]' % gene_list.name)
            self.all_gene_lists[gene_list.name] = set(g.gene_id for g in gene_list.genelistitem_set.all())
            for g in gene_list.genelistitem_set.all():
                self.gene_to_gene_lists[g.gene_id].add(gene_list.name)

        print("starting... ")
        gene_to_projects = defaultdict(set)
        gene_to_variants = defaultdict(set)
        gene_to_families = defaultdict(set)
        gene_to_variant_tags = defaultdict(set)
        gene_to_variant_and_families = defaultdict(lambda: defaultdict(set))

        Key = namedtuple('Key', 'gene_id, gene_name')
        project_ids = defaultdict(int)
        for variant_tag in tqdm(VariantTag.objects.filter(), unit=' variants'):
            project_tag = variant_tag.project_tag
            project_id = project_tag.project.project_id
            project_ids[project_id] += 1
            tag_name = project_tag.tag.lower()

            variant = get_datastore(project_id).get_single_variant(
                project_id,
                variant_tag.family.family_id,
                variant_tag.xpos,
                variant_tag.ref,
                variant_tag.alt,
            )

            # print(gene_to_projects)
            if variant is None:
                #print("Variant %s no longer called in this family (did the callset version change?)" % (variant_tag.toJSON()))
                continue

            #print(project_id,variant.toJSON()['gene_ids'])
            if variant.gene_ids is not None:
                for gene_id in variant.gene_ids:
                    gene_name = get_reference().get_gene_symbol(gene_id)
                    key = Key._make([gene_id, gene_name])
                    variant_id = "%s-%s-%s-%s" % (variant.chr, variant.pos, variant.ref, variant.alt)
                    gene_to_variants[key].add(variant_id)
                    if variant_tag.family:
                        gene_to_families[key].add(variant_tag.family)
                    gene_to_variant_tags[key].add(tag_name)
                    gene_to_projects[key].add(project_id.lower())
                    gene_to_variant_and_families[key][variant_id].add(variant_tag.family.family_id)
            
            if len(gene_to_projects) % 50 == 0:
                self.print_out(gene_to_projects, gene_to_families, gene_to_variants, gene_to_variant_tags, gene_to_variant_and_families)

        self.print_out(gene_to_projects, gene_to_families, gene_to_variants, gene_to_variant_tags, gene_to_variant_and_families)

    def print_out(self, gene_to_projects, gene_to_families, gene_to_variants, gene_to_variant_tags, gene_to_variant_and_families):
        output_filename = os.path.abspath("find_shared_tagged_genes.tsv")
        print("Saving output to " + output_filename)
        with open(output_filename, 'w') as f:
            f.write("\t".join(['gene_id', 'gene_name', 'in_MYOSEQ_gene_list', 'in_CMG_Discovery_gene_list', 'in_OMIM', 'gene_lists', 'tags', 'n_projects', 'projects', 'n_families', 'families', 'n_variants', 'variants', 'variants_and_families', 'family_link_out']) + "\n")
            for key, projs in sorted(gene_to_projects.items(), key=lambda gene_id_and_projs: len(gene_id_and_projs[1])):
                projs = sorted(list(projs), reverse=True)
                projs_filtered = []
                prefixes = set()
                for proj in projs:
                    prefix = proj.replace('-', '_').split("_")[0]
                    if prefix not in prefixes:
                        projs_filtered.append(proj)
                        prefixes.add(prefix)

                omim_records = OMIM.objects.filter(gene_id=key.gene_id)
                if omim_records:
                    in_omim = ', '.join(['https://www.omim.org/entry/%s' % omim_number for omim_number in set(omim_record.mim_number for omim_record in omim_records)])
                else:
                    in_omim = ""

                projs = projs_filtered
                variants = gene_to_variants[key]
                families = gene_to_families[key]
                tags = gene_to_variant_tags[key]

                if len(families) < 2:
                    continue
                gene_lists = ", ".join(self.gene_to_gene_lists.get(key.gene_id, []))
                line = "\t".join(map(str, [
                            key.gene_id, 
                            key.gene_name or "", 
                            "yes" if key.gene_id in self.all_gene_lists['MYOSEQ Gene List'] else "", 
                            "yes" if key.gene_id in self.all_gene_lists['CMG Discovery'] else "", 
                            in_omim,
                            gene_lists,
                            ", ".join(tags),
                            len(projs),
                            ", ".join(projs), 
                            len(families), 
                            ", ".join([fam.family_id for fam in families]), 
                            len(variants), 
                            ", ".join(variants),
                            ", ".join(["%s (%s)" % (v_and_f[0], ", ".join(v_and_f[1])) for v_and_f in gene_to_variant_and_families[key].items()]),
                            ", ".join(["https://seqr.broadinstitute.org/project/%s/family/%s" % (fam.project.project_id, fam.family_id) for fam in families]),
                            ])) + "\n"
                f.write(line)
                #print(line)
