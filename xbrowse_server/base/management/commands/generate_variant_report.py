import sys
import urllib
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ProjectTag, VariantTag, Individual
from xbrowse_server.mall import get_mall
from xbrowse import genomeloc
import vcf

monkol_muscle_disease_gene_list_2015_03_25 = ['ABHD5', 'ACADS', 'ACADVL', 'ACTA1', 'AGK', 'AGL', 'AGRN', 'ALG13', 'ALG14', 'ALG2', 'ANO5', 'AR', 'ATP2A1', 'B3GALNT2', 'B3GNT1', 'BAG3', 'BIN1', 'C10orf2', 'CAPN3', 'CAV3', 'CCDC78', 'CFL2', 'CHAT', 'CHKB', 'CHRNA1', 'CHRNB1', 'CHRND', 'CHRNE', 'CHRNG', 'CLCN1', 'CNBP', 'CNTN1', 'COL12A1', 'COL6A1', 'COL6A2', 'COL6A3', 'COLQ', 'COX15', 'CPT2', 'CRYAB', 'DAG1', 'DES', 'DMD', 'DMPK', 'DNAJB6', 'DNM2', 'DOK7', 'DOLK', 'DPAGT1', 'DPM1', 'DPM2', 'DPM3', 'DYSF', 'EMD', 'ENO3', 'ETFA', 'ETFB', 'ETFDH', 'FAM111B', 'FHL1', 'FKBP14', 'FKRP', 'FKTN', 'FLNC', 'GAA', 'GBE1', 'GFPT1', 'GMPPB', 'GNE', 'GYG1', 'GYS1', 'HNRNPDL', 'ISCU', 'IGHMBP2', 'ISPD', 'ITGA7', 'KBTBD13', 'KCNJ2', 'KLHL40', 'KLHL41', 'KLHL9', 'LAMA2', 'LAMB2', 'LAMP2', 'LARGE', 'LDB3', 'LDHA', 'LIMS2', 'LMNA', 'LPIN1', 'LRP4', 'MATR3', 'MEGF10', 'MSTN', 'MTM1', 'MTMR14', 'MTTP', 'MUSK', 'MYBPC3', 'MYF6', 'MYH14', 'MYH2', 'MYH3', 'MYH7', 'MYOT', 'NEB', 'OPA1', 'ORAI1', 'PABPN1', 'PFKM', 'PGAM2', 'PGK1', 'PGM1', 'PHKA1', 'PLEC', 'PNPLA2', 'POLG', 'POLG2', 'POMGNT1', 'POMGNT2', 'POMK', 'POMT1', 'POMT2', 'PREPL', 'PRKAG2', 'PTPLA', 'PTRF', 'PYGM', 'RAPSN', 'RRM2B', 'RYR1', 'SCN4A', 'SEPN1', 'SGCA', 'SGCB', 'SGCD', 'SGCG', 'SIL1', 'SLC22A5', 'SLC25A20', 'SLC25A4', 'SLC52A3', 'SMN1', 'STIM1', 'STIM2', 'SUCLA2', 'SYNE1', 'SYNE2', 'TAZ', 'TCAP', 'TIA1', 'TK2', 'TMEM43', 'TMEM5', 'TNNI2', 'TNNT1', 'TNNT3', 'TNPO3', 'TOR1AIP1', 'TPM2', 'TPM3', 'TRAPPC11', 'TRIM32', 'TTN', 'UBA1', 'VAPB', 'VCP', 'VMA21', 'YARS2']

muscle_disease_gene_list = monkol_muscle_disease_gene_list_2015_03_25

from collections import OrderedDict
import re
gene_loc = OrderedDict()
with open("/mongo/data/reference_data/report/muscle_disease_genes.gtf") as f:
    for line in f:
        fields = line.strip('\n').split('\t')
        chrom = fields[0].replace("chr", "")
        if fields[2] != "gene":
            raise ValueError("Not a 'gene' record: " + line)
        start = int(fields[3])
        end = int(fields[4])
        m = re.search("gene_name[ ]\"([^ ]+)\";", line)
        gene_name = m.group(1)
        if gene_name in gene_loc:
            raise ValueError(gene_name + " already in gene_locations")
        gene_loc[gene_name] = (chrom, start, end)

if len(gene_loc) != len(muscle_disease_gene_list):
    raise ValueError("len(gene_loc) != len(muscle_disease_gene_list): %d != %d" % (len(gene_loc), len(muscle_disease_gene_list)))

clinvar_vcf_file = vcf.VCFReader(filename="/mongo/data/reference_data/clinvar/clinvar_20150305.vcf.gz")

clinsig_map = {
    0 : ("unknown", "Uncertain significance"),
    1 : ("untested", "not provided (includes the cases where data are not available or unknown)"),
    2 : ("non-pathogenic", "Benign"),
    3 : ("probable-non-pathogenic", "Likely benign"),
    4 : ("probable-pathogenic", "Likely pathogenic"),
    5 : ("pathogenic", "Pathogenic"),
    6 : ("drug-response", "drug response"),
    7 : ("histocompatibility", "histocompatibility"),
    255 : ("other", "other, confers sensitivity, risk factor, association, protective"),
}


genotype_map = {0: "ref", 1: "het", 2: "hom"}


class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def get_output_row(self, variant, ref, alt, individual_id, family):
        v = variant
        if individual_id not in v.genotypes:
            print("skipping variant: %s because individual %s not in %s"  % (str(v.xpos)+ " " + v.ref + ">" + v.alt, individual_id, family.family_id))
            return None
        
        genotype = v.genotypes[individual_id]
        if genotype.gq is None:
            print("skipping variant: %s because this variant is not called in this individual (%s)"  % (str(v.xpos)+" " + v.ref + ">" + v.alt, individual_id)) #, str(genotype)))
            return None

        xpos = variant.xpos
        chrom, pos = genomeloc.get_chr_pos(xpos)

        annot = v.annotation
        vep = annot["vep_annotation"][annot["worst_vep_annotation_index"]]  # ea_maf, swissprot, existing_variation, pubmed, aa_maf, ccds, high_inf_pos, cdna_position, canonical, tsl, feature_type, intron, trembl, feature, codons, polyphen, clin_sig, motif_pos, protein_position, afr_maf, amino_acids, cds_position, symbol, uniparc, eur_maf, hgnc_id, consequence, sift, exon, biotype, is_nc, gmaf, motif_name, strand, motif_score_change, distance, hgvsp, ensp, allele, symbol_source, amr_maf, somatic, hgvsc, asn_maf, is_nmd, domains, gene

        gene_name = vep["symbol"]  # vep["gene"]

        if genotype.num_alt is None:
            s = "\n\n"
            for i, g in v.genotypes.items():
                s += str(i) + ": " + str(g) + "\n"
            raise ValueError("genotype.num_alt is None: " + str(genotype) + "\n" + str(v.toJSON()) + "\n" + s)

        genotype_str = genotype_map[genotype.num_alt]
        
        variant_str = "%s:%s %s>%s" % (chrom, pos, ref, alt)
        hgvs_c = urllib.unquote(vep["hgvsc"])
        hgvs_p = urllib.unquote(vep["hgvsp"])
        rsid = annot["rsid"] or ""
        
        #rsid = vep["clinvar_rs"]

        exac_af_all = str(annot["freqs"]["exac"])
        exac_af_pop_max = ""
                
        clinvar_clinsig = ""
        clinvar_clnrevstat = ""
        
        clinvar_clinsig_from_dbnsfp = vep["clin_sig"]
        
        clinvar_records = [record for record in clinvar_vcf_file.fetch(chrom.replace("chr", ""), pos, pos) if record.POS == pos and record.REF == ref]
        
                
        #if clinvar_clinsig_from_dbnsfp or clinvar_records:
            # defensive programming
            #if clinvar_clinsig_from_dbnsfp and not clinvar_records:
            #    raise ValueError("record has dbNSFP clinvar entry but is not in clinvar vcf: %s" % variant_str)
            #if not clinvar_clinsig_from_dbnsfp and clinvar_records:
            #    raise ValueError("record doesn't have a dbNSFP clinvar entry but is in clinvar vcf: %s" % variant_str)

        if clinvar_records:
            #if len(clinvar_records) > 1:
            #    raise ValueError("multiple clinvar records found for variant: %s" % variant_str)
            clinvar_record = clinvar_records[-1]
            clinvar_allele_indexes = map(int, clinvar_record.INFO["CLNALLE"])
            clinvar_alleles = map(str, [clinvar_record.REF] + clinvar_record.ALT)
            xbrowse_alleles = map(str, [ref] + [alt])
            clinvar_value_indexes_to_use = [i for i, clinvar_allele_index in enumerate(clinvar_allele_indexes) if str(clinvar_alleles[clinvar_allele_index]).upper() in xbrowse_alleles]
            clnrevstat = clinvar_record.INFO["CLNREVSTAT"]
            clnrevstat = [clnrevstat[i] for i in clinvar_value_indexes_to_use]
            clnsig = clinvar_record.INFO["CLNSIG"]
            clnsig = [clnsig[i] for i in clinvar_value_indexes_to_use]  
            # print("Fetched clinvar %s: %s"% (clinvar_record, clinvar_record.INFO))
            if clnsig:
                clinvar_clinsig_numbers = map(int, clnsig[0].split("|")) 
                clinvar_clinsig = "|".join(set([clinsig_map[clinvar_clinsig_number][0] for clinvar_clinsig_number in clinvar_clinsig_numbers]))

                clinvar_clnrevstat = "|".join(set(clnrevstat[0].split("|")))

        comments = ""
        row = map(str, [gene_name, genotype_str, variant_str, hgvs_c, hgvs_p, rsid, exac_af_all, exac_af_pop_max, clinvar_clinsig, clinvar_clnrevstat, comments])
        return row
        
    def handle(self, *args, **options):
        if len(args) < 1:
            print("Please provide the project_id. The individual_id(s) are optional")
            return

        project_id = args[0]

        individual_ids = args[1:]
        
        try:
            project = Project.objects.get(project_id=project_id)
        except ObjectDoesNotExist:
            sys.exit("Invalid project id: " + project_id)
            
        try:
            if individual_ids:
                individual_ids = [Individual.objects.get(project=project, indiv_id=individual_id) for individual_id in individual_ids]
            else:
                individual_ids = [i for i in Individual.objects.filter(project=project)]
        except ObjectDoesNotExist:
            sys.exit("Invalid individual ids: " + str(individual_ids))
        

        for i in individual_ids:
            self.handle_individual(project, i)
        

    def handle_individual(self, project, individual):
        project_id = project.project_id
        individual_id = individual.indiv_id
        
        variant_tags_in_this_family = VariantTag.objects.filter(project_tag__project=project, project_tag__tag="REPORT", family=individual.family)
        if len(list(variant_tags_in_this_family)) == 0:
            print("skipping individual %s since no variants are tagged in family %s..." % (individual_id, individual.family.family_id))
            return

        header = ["gene_name", "genotype", "variant", "hgvs_c", "hgvs_p", "rsid", "exac_af_all", "exac_af_pop_max", "clinvar_clinsig", "clinvar_clnrevstat", "comments"]
        with open("report_for_%s_%s.flagged.txt" % (project_id, individual_id), "w") as out:
            #print("\t".join(header))
            out.write("\t".join(header) + "\n")

            # get variants that have been tagged
            for variant_tag in VariantTag.objects.filter(project_tag__project=project, project_tag__tag="REPORT", family=individual.family):
                xpos = variant_tag.xpos
                chrom, pos = genomeloc.get_chr_pos(xpos)
                ref = variant_tag.ref
                for alt in [variant_tag.alt]:  
                    v = get_mall().variant_store.get_single_variant(project_id, individual.family.family_id, xpos, ref, alt) 
                    if v is None:
                        raise ValueError("Couldn't find variant in variant store for: ", project_id, individual.family.family_id, xpos, ref, alt, variant_tag.toJSON())

                    row = self.get_output_row(v, ref, alt, individual.indiv_id, individual.family)
                    if row is None:
                        continue
                    #print("\t".join(row))
                    out.write("\t".join(row) + "\n")
                                
                #print(variant_tag.project_tag.title, variant_tag.project_tag.tag,  variant_tag.xpos, variant_tag.ref, variant_tag.alt)


        with open("report_for_%s_%s.genes.txt" % (project_id, individual_id), "w") as out:
            header = ["gene_chrom", "gene_start", "gene_end"] + header + ["json_dump"]
            #print("\t".join(header))
            out.write("\t".join(header) + "\n")
            for gene_name, (chrom, start, end) in gene_loc.items():
                xpos_start = genomeloc.get_single_location("chr" + chrom, start)
                xpos_end = genomeloc.get_single_location("chr" + chrom, end)
                for v in get_mall().variant_store.get_variants_in_range(project_id, individual.family.family_id, xpos_start, xpos_end):
                    json_dump = str(v.genotypes)
                    for alt in v.alt.split(","):  
                        row = self.get_output_row(v, v.ref, alt, individual.indiv_id, individual.family)
                        if row is None:
                            continue
                        row = map(str, [chrom, start, end] + row + [json_dump])
                        #print("\t".join(row))
                        out.write("\t".join(row) + "\n")
