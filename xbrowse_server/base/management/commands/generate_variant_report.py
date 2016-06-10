import urllib
from xbrowse.utils.minirep import get_minimal_representation
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from xbrowse.annotation import vep_annotations
from xbrowse_server.base.models import Project, VariantTag, Individual, VariantNote
from xbrowse_server.mall import get_mall
from xbrowse import genomeloc
import vcf
import sys
from collections import OrderedDict, defaultdict
import re
import urllib2

monkol_muscle_disease_gene_list_2015_03_25 = ['ABHD5', 'ACADS', 'ACADVL', 'ACTA1', 'AGK', 'AGL', 'AGRN', 'ALG13', 'ALG14', 'ALG2', 'ANO5', 'AR', 'ATP2A1', 'B3GALNT2', 'B3GNT1', 'BAG3', 'N1', 'C10orf2', 'CAPN3', 'CAV3', 'CCDC78', 'CFL2', 'CHAT', 'CHKB', 'CHRNA1', 'CHRNB1', 'CHRND', 'CHRNE', 'CHRNG', 'CLCN1', 'CNBP', 'CNTN1', 'COL12A1', 'COL6A1', 'COL6A2', 'COL6A3', 'COLQ', 'COX15', 'CPT2', 'CRYAB', 'DAG1', 'DES', 'DMD', 'DMPK', 'DNAJB6', 'DNM2', 'DOK7', 'DOLK', 'DPAGT1', 'DPM1', 'DPM2', 'DPM3', 'DYSF', 'EMD', 'ENO3', 'ETFA', 'ETFB', 'ETFDH', 'FAM111B', 'FHL1', 'FKBP14', 'FKRP', 'FKTN', 'FLNC', 'GAA', 'GBE1', 'GFPT1', 'GMPPB', 'GNE', 'GYG1', 'GYS1', 'HNRNPDL', 'ISCU', 'IGHMBP2', 'ISPD', 'ITGA7', 'KBTBD13', 'KCNJ2', 'KLHL40', 'KLHL41', 'KLHL9', 'LAMA2', 'LAMB2', 'LAMP2', 'LARGE', 'LDB3', 'LDHA', 'LIMS2', 'LMNA', 'LPIN1', 'LRP4', 'MATR3', 'MEGF10', 'MSTN', 'MTM1', 'MTMR14', 'MTTP', 'MUSK', 'MYBPC3', 'MYF6', 'MYH14', 'MYH2', 'MYH3', 'MYH7', 'MYOT', 'NEB', 'OPA1', 'ORAI1', 'PABPN1', 'PFKM', 'PGAM2', 'PGK1', 'PGM1', 'PHKA1', 'PLEC', 'PNPLA2', 'POLG', 'POLG2', 'POMGNT1', 'POMGNT2', 'POMK', 'POMT1', 'POMT2', 'PREPL', 'PRKAG2', 'PTPLA', 'PTRF', 'PYGM', 'RAPSN', 'RRM2B', 'RYR1', 'SCN4A', 'SEPN1', 'SGCA', 'SGCB', 'SGCD', 'SGCG', 'SIL1', 'SLC22A5', 'SLC25A20', 'SLC25A4', 'SLC52A3', 'SMN1', 'STIM1', 'STIM2', 'SUCLA2', 'SYNE1', 'SYNE2', 'TAZ', 'TCAP', 'TIA1', 'TK2', 'TMEM43', 'TMEM5', 'TNNI2', 'TNNT1', 'TNNT3', 'TNPO3', 'TOR1AIP1', 'TPM2', 'TPM3', 'TRAPPC11', 'TRIM32', 'TTN', 'UBA1', 'VAPB', 'VCP', 'VMA21', 'YARS2']

myoseq_gene_list_2015_11_30 = ['ABHD5', 'ACADS', 'ACADVL', 'ACTA1', 'AGK', 'AGL', 'AGRN', 'ALG13', 'ALG14', 'ALG2', 'ANO5', 'ATP2A1', 'B3GALNT2', 'B3GNT1', 'BAG3', 'BIN1', 'C10orf2', 'CAPN3', 'CAV3', 'CCDC78', 'CFL2', 'CHAT', 'CHKB', 'CHRNA1', 'CHRNB1', 'CHRND', 'CHRNE', 'CHRNG', 'CLCN1', 'CNBP', 'CNTN1', 'COL12A1', 'COL6A1', 'COL6A2', 'COL6A3', 'COLQ', 'COX15', 'CPT2', 'CRYAB', 'DAG1', 'DES', 'DMD', 'DNAJB6', 'DNM2', 'DOK7', 'DOLK', 'DPAGT1', 'DPM1', 'DPM2', 'DPM3', 'DYSF', 'EMD', 'ENO3', 'ETFA', 'ETFB', 'ETFDH', 'FAM111B', 'FHL1', 'FKBP14', 'FKRP', 'FKTN', 'FLNC', 'GAA', 'GBE1', 'GFPT1', 'GMPPB', 'GNE', 'GYG1', 'GYS1', 'HNRNPDL', 'ISCU', 'IGHMBP2', 'ISPD', 'ITGA7', 'KBTBD13', 'KCNJ2', 'KLHL40', 'KLHL41', 'KLHL9', 'LAMA2', 'LAMB2', 'LAMP2', 'LARGE', 'LDB3', 'LDHA', 'LIMS2', 'LMNA', 'LPIN1', 'LRP4', 'MATR3', 'MEGF10', 'MSTN', 'MTM1', 'MTMR14', 'MTTP', 'MUSK', 'MYBPC3', 'MYF6', 'MYH14', 'MYH2', 'MYH3', 'MYH7', 'MYOT', 'NEB', 'OPA1', 'ORAI1', 'PABPN1', 'PFKM', 'PGAM2', 'PGK1', 'PGM1', 'PHKA1', 'PLEC', 'PNPLA2', 'POLG', 'POLG2', 'POMGNT1', 'POMGNT2', 'POMK', 'POMT1', 'POMT2', 'PREPL', 'PRKAG2', 'PTPLA', 'PTRF', 'PYGM', 'RAPSN', 'RRM2B', 'RYR1', 'SCN4A', 'SEPN1', 'SGCA', 'SGCB', 'SGCD', 'SGCG', 'SIL1', 'SLC22A5', 'SLC25A20', 'SLC25A4', 'SLC52A3', 'SMCHD1', 'STAC3', 'STIM1', 'STIM2', 'SUCLA2', 'SYNE1', 'SYNE2', 'TAZ', 'TARDBP', 'TCAP', 'TIA1', 'TK2', 'TMEM43', 'TMEM5', 'TNNI2', 'TNNT1', 'TNNT3', 'TNPO3', 'TOR1AIP1', 'TPM2', 'TPM3', 'TRAPPC11', 'TRIM32', 'TTN', 'UBA1', 'VAPB', 'VCP', 'VMA21', 'YARS2']

muscle_disease_gene_list = myoseq_gene_list_2015_11_30
muscle_disease_gene_set = set(muscle_disease_gene_list)

assert len(muscle_disease_gene_set) == len(muscle_disease_gene_list)
exac_vcf = vcf.VCFReader(filename="/mongo/data/reference_data/ExAC.r0.3.sites.vep.vcf.gz")

def get_exac_af(chrom, pos, ref, alt):
    populations = ['AMR', 'EAS', 'FIN', 'NFE', 'SAS', 'AFR']

    chrom_without_chr = chrom.replace("chr", "")
    xpos = genomeloc.get_single_location(chrom, pos)
    variant_length = len(ref) + len(alt)

    # check whether the alleles match
    matching_exac_variant = None
    matching_exac_variant_i = None
    for record in exac_vcf.fetch(chrom_without_chr, pos - variant_length, pos + variant_length):
        exac_xpos = genomeloc.get_xpos(record.CHROM, record.POS)
        for exac_alt_i, exac_alt in enumerate(record.ALT):
            exac_variant_xpos, exac_ref, exac_alt = get_minimal_representation(exac_xpos, str(record.REF), str(exac_alt))
            if exac_variant_xpos == xpos and exac_ref == ref and exac_alt == alt:
                if matching_exac_variant is not None:
                    print("ERROR: multiple exac variants match the variant: %s %s %s %s" % (chrom, pos, ref, alt))
                matching_exac_variant = record
                matching_exac_variant_i = exac_alt_i
                #print("Variant %s %s %s matches: %s %s %s %s" % (xpos, ref, alt, record, exac_variant_xpos, exac_ref, exac_alt) )

    if matching_exac_variant is None:
        #print("Variant %s %s %s %s not found in ExAC" % (chrom, pos, alt, ref))
        return None, None, None

    pop_max_af = -1
    pop_max_population = None
    for p in populations:
        if matching_exac_variant.INFO['AN_'+p] > 0:
            pop_af = matching_exac_variant.INFO['AC_'+p][matching_exac_variant_i]/float(matching_exac_variant.INFO['AN_'+p])
            if pop_af > pop_max_af:
                pop_max_af = pop_af
                pop_max_population = p


    if matching_exac_variant.INFO['AN_Adj'] != 0:
        global_af = float(matching_exac_variant.INFO['AC_Adj'][matching_exac_variant_i])/float(matching_exac_variant.INFO['AN_Adj'])
    else:
        assert float(matching_exac_variant.INFO['AC_Adj'][matching_exac_variant_i]) == 0
        global_af = 0

    return global_af, pop_max_af, pop_max_population

gene_loc = OrderedDict()
with open("/mongo/data/reference_data/report/muscle_disease_genes.gtf") as f:
    for line in f:
        fields = line.strip('\n').split('\t')
        chrom = fields[0].replace("chr", "")
        if fields[2] != "gene":
            raise ValueError("Not a 'gene' record: " + line)
        start = int(fields[3])
        end = int(fields[4])
        m = re.search("gene_id[ ]\"([^ ]+)\";", line)
        gene_id = m.group(1)
        if gene_id in gene_loc:
            raise ValueError(gene_id + " already in gene_locations")
        gene_loc[gene_id] = (chrom, start, end)

if len(gene_loc) != len(muscle_disease_gene_list):
    raise ValueError("len(gene_loc) != len(muscle_disease_gene_list): %d != %d" % (len(gene_loc), len(muscle_disease_gene_list)))

clinvar_vcf_file = vcf.VCFReader(filename="/mongo/data/reference_data/clinvar.vcf.gz")

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

    def get_output_row(self, variant, xpos, ref, alt, individual_id, family, all_fields=False, comments="", gene_id=""):
        v = variant
        if individual_id not in v.genotypes:
            print("skipping variant: %s because individual %s not in %s" % (str(xpos) + " " + ref + ">" + alt, individual_id, family.family_id))
            return None

        gene_id = gene_id.split(".")[0] if gene_id else None  # strip off the gene_id suffix (eg. '.3')

        genotype = v.genotypes[individual_id]
        if genotype.gq is None:
            print("skipping variant: %s because this variant is not called in this individual (%s)"  % (str(xpos)+" " + ref + ">" + alt, individual_id)) #, str(genotype)))
            return None

        chrom, pos = genomeloc.get_chr_pos(xpos)
        chrom_without_chr = chrom.replace("chr", "")

        annot = v.annotation
        if gene_id:
            worst_vep_annotation_index = vep_annotations.get_worst_vep_annotation_index(annot["vep_annotation"], gene_id = gene_id)
        else:
            # create dictionary that maps gene id to the index of the worst vep annotation for that gene
            protein_coding_gene_ids = set(a['gene'] for a in annot["vep_annotation"] if a['biotype'] == 'protein_coding')
            if not protein_coding_gene_ids:
                print("skipping variant %s in this individual (%s) because none of the transcripts are protein coding: %s"  % (str(xpos)+" " + ref + ">" + alt, individual_id, annot))
                return None

            worst_vep_annotation_index = vep_annotations.get_worst_vep_annotation_index(annot["vep_annotation"], gene_id=protein_coding_gene_ids)
            if len(protein_coding_gene_ids) > 1:
                selected_gene_id = annot["vep_annotation"][worst_vep_annotation_index]['gene']
                print("Selected %s from %s" % (annot["vep_annotation"][worst_vep_annotation_index]['symbol'], set([a['symbol'] for a in annot["vep_annotation"] if a['gene'] in protein_coding_gene_ids])))

        vep = annot["vep_annotation"][worst_vep_annotation_index]  # ea_maf, swissprot, existing_variation, pubmed, aa_maf, ccds, high_inf_pos, cdna_position, canonical, tsl, feature_type, intron, trembl, feature, codons, polyphen, clin_sig, motif_pos, protein_position, afr_maf, amino_acids, cds_position, symbol, uniparc, eur_maf, hgnc_id, consequence, sift, exon, biotype, is_nc, gmaf, motif_name, strand, motif_score_change, distance, hgvsp, ensp, allele, symbol_source, amr_maf, somatic, hgvsc, asn_maf, is_nmd, domains, gene

        worst_vep_annotation_index = vep_annotations.get_worst_vep_annotation_index(annot["vep_annotation"])

        vep = annot["vep_annotation"][worst_vep_annotation_index]

        if "symbol" in vep and "consequence"in vep:
            gene_name = vep["symbol"]  # vep["gene"]
            functional_class = vep["consequence"]
        else:
            gene_name = functional_class = ""
            print("ERROR: gene_name and functional_class not found in annot['vep_annotation'][annot['worst_vep_annotation_index']]: %(vep)s" % locals())
        if genotype.num_alt is None:
            s = "\n\n"
            for i, g in v.genotypes.items():
                s += str(i) + ": " + str(g) + "\n"
            raise ValueError("genotype.num_alt is None: " + str(genotype) + "\n" + str(v.toJSON()) + "\n" + s)

        genotype_str = genotype_map[genotype.num_alt]

        variant_str = "%s:%s %s>%s" % (chrom, pos, ref, alt)
        if "hgvsc" in vep and "hgvsp"in vep:
            #print("hgvs_c and/or hgvs_p WAS found in annot['vep_annotation'][annot['worst_vep_annotation_index']]: %(vep)s" % locals())
            hgvs_c = urllib.unquote(vep["hgvsc"])
            hgvs_p = urllib.unquote(vep["hgvsp"])
        else:
            hgvs_c = hgvs_p = ""
            #print("ERROR: hgvs_c and/or hgvs_p not found in annot['vep_annotation'][annot['worst_vep_annotation_index']]: %(vep)s" % locals())

        rsid = annot["rsid"] or ""

        #rsid = vep["clinvar_rs"]

        exac_global_af, exac_popmax_af, exac_popmax_population = get_exac_af(chrom, pos, ref, alt)
        if exac_global_af is None:
             exac_global_af, exac_popmax_af, exac_popmax_population = 0, 0, "[variant not found in ExACv0.3]"
        else:
            exac_global_af_annot = str(annot["freqs"]["exac_v3"])
            if abs(float(exac_global_af) - float(exac_global_af_annot)) > 0.01:
                print("Error annot['freqs']['exac_v3']  (%s) doesn't match %s" % (float(exac_global_af), float(exac_global_af_annot)))

        clinvar_clinsig = ""
        clinvar_clnrevstat = ""

        if "clin_sig" in vep:
            clinvar_clinsig_from_dbnsfp = vep["clin_sig"]
        else:
            clinvar_clinsig_from_dbnsfp = ""
            #print("ERROR: clin_sig not found in annot['vep_annotation'][annot['worst_vep_annotation_index']]: %(vep)s" % locals())


        clinvar_records = [record for record in clinvar_vcf_file.fetch(chrom_without_chr, pos, pos) if record.POS == pos and record.REF == ref]


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

        # get
        number_of_stars = "[not found]" if all_fields else "[not retrieved to save time]"
        clinvar_url = "http://www.ncbi.nlm.nih.gov/clinvar/?term="+chrom_without_chr+"[chr]+AND+"+str(pos)+"[chrpos37]"
        if clinvar_clinsig and all_fields:
            print("Reading from: " + clinvar_url)
            url_opener = urllib2.build_opener()
            url_opener.addheaders = [('User-agent', "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11")]
            page_contents = url_opener.open(clinvar_url).read()
            match = re.search("(\d) star.? out of maximum of 4 stars", page_contents)
            if match:
                number_of_stars = int(match.group(1))
            else:
                print("No match in page: " + clinvar_url)
                for line in page_contents.split("\n"):
                    if "rev_stat_text hide" in line:
                        print(" -- this line was expected to contain number of stars: " + line)

        row = map(str, [gene_name, genotype_str, variant_str, functional_class, hgvs_c, hgvs_p, rsid, exac_global_af, exac_popmax_af, exac_popmax_population, clinvar_clinsig, clinvar_clnrevstat, number_of_stars, clinvar_url, comments])
        return row

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
    
    def handle(self, *args, **options):
        if len(args) < 1:
            print("Please provide the project_id. The individual_id(s) are optional")
            return

        project_id = args[0]

        try:
            project = Project.objects.get(project_id=project_id)
        except ObjectDoesNotExist:
            sys.exit("Invalid project id: " + project_id)

        individual_ids = args[1:]
        try:
            if individual_ids:
                individual_ids = [Individual.objects.get(project=project, indiv_id=individual_id) for individual_id in individual_ids]
            else:
                individual_ids = [i for i in Individual.objects.filter(project=project)]
        except ObjectDoesNotExist:
            sys.exit("Invalid individual ids: " + str(individual_ids))

        for i in individual_ids:
            family_collection = get_mall(project_id).variant_store._get_family_collection(project_id, i.family.family_id)
            if family_collection is None:
                print("WARNING: Family %s data not loaded in variant datastore. Skipping individual %s." % (i.family.family_id, i))
                continue
            self.handle_individual(project, i)
        print("Finished generating report")

    def handle_individual(self, project, individual):
        project_id = project.project_id
        individual_id = individual.indiv_id

        print("Processing individual %s" % individual_id)
        # get variants that have been tagged or that have a note that starts with "REPORT"
        variants_in_report_and_notes = defaultdict(str)
        for vt in VariantTag.objects.filter(project_tag__project=project,
                                            project_tag__tag="REPORT",
                                            family=individual.family):

            variants_in_report_and_notes[(vt.xpos, vt.ref, vt.alt)] = ""

        for vn in VariantNote.objects.filter(project=project, family=individual.family):
            if vn.note and vn.note.strip().startswith("REPORT"):
                variants_in_report_and_notes[(vn.xpos, vn.ref, vn.alt)] = ""

        header = ["gene_name", "genotype", "variant", "functional_class",
                  "hgvs_c", "hgvs_p", "rsid",
                  "exac_global_af", "exac_pop_max_af", "exac_pop_max_population",
                  "clinvar_clinsig", "clinvar_clnrevstat", "number_of_stars",
                  "clinvar_url", "comments"]

        if len(variants_in_report_and_notes) != 0:
            with open("report_for_%s_%s.flagged.txt" % (project_id, individual_id), "w") as out:
                #print("\t".join(header))
                out.write("\t".join(header) + "\n")

                # retrieve text of all notes that were left for any of these variants
                for vn in VariantNote.objects.filter(project=project, family=individual.family):
                    if vn.note and (vn.xpos, vn.ref, vn.alt) in variants_in_report_and_notes:
                        other_notes = variants_in_report_and_notes[(vn.xpos, vn.ref, vn.alt)]
                        if len(other_notes) > 0:
                            other_notes += "||"
                        variants_in_report_and_notes[(vn.xpos, vn.ref, vn.alt)] = other_notes + "%s|%s|%s" % (vn.date_saved, vn.user.email, vn.note.strip())

                for (xpos, ref, alt), notes in variants_in_report_and_notes.items():

                    #chrom, pos = genomeloc.get_chr_pos(xpos)

                    v = get_mall(project_id).variant_store.get_single_variant(project_id, individual.family.family_id, xpos, ref, alt)
                    if v is None:
                        raise ValueError("Couldn't find variant in variant store for: %s, %s, %s %s %s" % (project_id, individual.family.family_id, xpos, ref, alt))

                    row = self.get_output_row(v, xpos, ref, alt, individual_id, individual.family, all_fields=True, comments=notes)
                    if row is None:
                        continue
                    #print("\t".join(row))
                    out.write("\t".join(row) + "\n")

                #print(variant_tag.project_tag.title, variant_tag.project_tag.tag,  variant_tag.xpos, variant_tag.ref, variant_tag.alt)


        with open("report_for_%s_%s.genes.txt" % (project_id, individual_id), "w") as out:
            header = ["gene_chrom", "gene_start", "gene_end"] + header + ["json_dump"]
            #print("\t".join(header))
            out.write("\t".join(header) + "\n")
            for gene_id, (chrom, start, end) in gene_loc.items():
                xpos_start = genomeloc.get_single_location("chr" + chrom, start)
                xpos_end = genomeloc.get_single_location("chr" + chrom, end)
                for v in get_mall(project_id).variant_store.get_variants_in_range(project_id, individual.family.family_id, xpos_start, xpos_end):

                    json_dump = str(v.genotypes)
                    try:
                        notes = variants_in_report_and_notes[(v.xpos, v.ref, v.alt)]
                    except KeyError:
                        notes = ""
                    row = self.get_output_row(v, v.xpos, v.ref, v.alt, individual_id, individual.family, comments=notes, gene_id=gene_id)
                    if row is None:
                        continue
                    row = map(str, [chrom, start, end] + row + [json_dump])

                    #print("\t".join(row))
                    out.write("\t".join(row) + "\n")

