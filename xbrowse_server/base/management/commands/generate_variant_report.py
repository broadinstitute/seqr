import sys
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ProjectTag, VariantTag, Individual
from xbrowse_server.mall import get_mall
from xbrowse import genomeloc
import pysam

clinvar_vcf_file = pysam.Tabixfile("/mongo/data/reference_data/clinvar/clinvar_20150305.vcf.gz")

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def handle(self, *args, **options):
        if len(args) < 2:
            print("Please provide the project_id and individual_id as command line args")
            return

        project_id = args[0]

        individual_id = args[1]
        
        try:
            project = Project.objects.get(project_id=project_id)
        except ObjectDoesNotExist:
            sys.exit("Invalid project id: " + project_id)
            
        try:
            individual = Individual.objects.get(project=project, indiv_id=individual_id)
        except ObjectDoesNotExist:
            sys.exit("Invalid individual id: " + individual_id)

        genotype_map = {0: "ref", 1: "het", 2: "hom"}
        with open("report_for_%s_%s.txt" % (project_id, individual_id), "w") as out:
            header = ["gene_name", "genotype", "variant", "hgvs_c", "hgvs_p", "rsid", "exac_af_all", "exac_af_pop_max", "clinvar_clinsig", "comments"]
            print("\t".join(header))
            out.write("\t".join(header) + "\n")

            # get variants that have been tagged
            for variant_tag in VariantTag.objects.filter(project_tag__project=project, project_tag__tag="report"):
                xpos = variant_tag.xpos
                chrom, pos = genomeloc.get_chr_pos(xpos)
                ref = variant_tag.ref            
                alt = variant_tag.alt
                family = variant_tag.family
                v = get_mall().variant_store.get_single_variant(project_id, family.family_id, xpos, ref, alt) 
                annot = v.annotation
                vep = annot["vep_annotation"][annot["worst_vep_annotation_index"]]  # ea_maf, swissprot, existing_variation, pubmed, aa_maf, ccds, high_inf_pos, cdna_position, canonical, tsl, feature_type, intron, trembl, feature, codons, polyphen, clin_sig, motif_pos, protein_position, afr_maf, amino_acids, cds_position, symbol, uniparc, eur_maf, hgnc_id, consequence, sift, exon, biotype, is_nc, gmaf, motif_name, strand, motif_score_change, distance, hgvsp, ensp, allele, symbol_source, amr_maf, somatic, hgvsc, asn_maf, is_nmd, domains, gene

                gene_name = vep["symbol"]  # vep["gene"]

                # genotype
                genotype = v.genotypes[individual_id]
                genotype_str = genotype_map[genotype.num_alt]
        
                variant_str = "%s:%s %s>%s" % (chrom, pos, ref, alt)
                hgvs_c = vep["hgvsc"]
                hgvs_p = vep["hgvsp"]
                rsid = annot["rsid"]
                #rsid = vep["clinvar_rs"]

                exac_af_all = str(annot["freqs"]["exac"])
                exac_af_pop_max = ""
                clinvar_clinsig = vep["clin_sig"]

                if clinvar_clinsig:
                    clinvar_record = clinvar_vcf_file.fetch(chrom, pos)
                    print("Fetched %s: "% (clinvar_record))


                comments = ""

                row = [gene_name, genotype_str, variant_str, hgvs_c, hgvs_p, rsid, exac_af_all, exac_af_pop_max, clinvar_clinsig, comments]
                print("\t".join(row))
                out.write("\t".join(row) + "\n")
                

                #print(variant_tag.project_tag.title, variant_tag.project_tag.tag,  variant_tag.xpos, variant_tag.ref, variant_tag.alt)

