import datetime
import os
import re
import sh
import tempfile
import vcf
from xbrowse import vcf_stuff

SO_SEVERITY_ORDER = [
    'transcript_ablation',
    'splice_donor_variant',
    "splice_acceptor_variant",
    'stop_gained',
    'frameshift_variant',
    'protein_altering_variant',
    'stop_lost',
    'initiator_codon_variant',
    'start_lost',
    'inframe_insertion',
    'inframe_deletion',
    'missense_variant',
    'transcript_amplification',
    'splice_region_variant',
    'incomplete_terminal_codon_variant',
    'synonymous_variant',
    'stop_retained_variant',
    'coding_sequence_variant',
    'mature_miRNA_variant',
    '5_prime_UTR_variant',
    '3_prime_UTR_variant',
    'intron_variant',
    'NMD_transcript_variant',
    'non_coding_exon_variant', 'non_coding_transcript_exon_variant',  # 2 terms due to name change in Ensembl v77
    'nc_transcript_variant', 'non_coding_transcript_variant',  # 2 terms due to name change in Ensembl v77
    'upstream_gene_variant',
    'downstream_gene_variant',
    'TFBS_ablation',
    'TFBS_amplification',
    'TF_binding_site_variant',
    'regulatory_region_variant',
    'regulatory_region_ablation',
    'regulatory_region_amplification',
    'feature_elongation',
    'feature_truncation',
    'intergenic_variant',
    ''
]

SO_SEVERITY_ORDER_POS = { t: i for i, t in enumerate(SO_SEVERITY_ORDER) }
CODING_POS_CUTOFF = SO_SEVERITY_ORDER_POS['coding_sequence_variant']

NUM_SO_TERMS = len(SO_SEVERITY_ORDER)


class HackedVEPAnnotator():
    """
    xBrowse depends on VEP annotations -
    This class is a wrapper around VEP that provides a pythonic interface to VEP annotations
    It should just call the REST API, but that is slow, so it spins out subprocesses :(
    """
    def __init__(self, vep_perl_path, vep_cache_dir, vep_batch_size=20000, human_ancestor_fa=None):
        self._vep_perl_path = vep_perl_path
        self._vep_cache_dir = vep_cache_dir
        self._vep_batch_size = vep_batch_size
        self._human_ancestor_fa = human_ancestor_fa

    def _run_vep(self, input_vcf, output_vcf):
        """
        Just run VEP to the xbrowse configurations
        """
        vep_command = [
            self._vep_perl_path,
            "--offline",
            "--cache",
            "--everything",  # http://useast.ensembl.org/info/docs/tools/vep/script/vep_options.html#opt_everything
            "--vcf",
            "--fork", "4",
            "--fasta", os.path.join(self._vep_cache_dir,
                "homo_sapiens/78_GRCh37/Homo_sapiens.GRCh37.75.dna.primary_assembly.fa"),
#            "--filter", "transcript_ablation,splice_donor_variant,splice_acceptor_variant,frameshift_variant,"
#                "stop_gained,stop_lost,initiator_codon_variant,transcript_amplification,"
#                "inframe_insertion,inframe_deletion,missense_variant,splice_region_variant,"
#                "incomplete_terminal_codon_variant,stop_retained_variant,synonymous_variant,coding_sequence_variant,"
#                "mature_miRNA_variant,5_prime_UTR_variant,3_prime_UTR_variant,intron_variant,NMD_transcript_variant,"
#                "TFBS_ablation,TFBS_amplification,TF_binding_site_variant",
            "--force_overwrite",
            "--dir", self._vep_cache_dir,
            "-i", input_vcf,
            "-o", output_vcf,
        ]

        if self._human_ancestor_fa is not None:
            vep_command += [
                "--plugin", "LoF,human_ancestor_fa:{}".format(self._human_ancestor_fa),
            ]

        print("Running VEP:\n" + " ".join(vep_command))
        sh.perl(vep_command)


    def get_vep_annotations_for_variants(self, variant_t_list):
        """
        Load annotations for a set of variants
        - write these annotations to a temporary vcf file
        - runs VEP on the temp VCF file
        - loads newly annotated VCF to annotator
        Obviously there should be a better way to do this, but this is what we have for now
        """


        def process_batch(variant_t_batch):
            vep_input_file_path = tempfile.mkstemp()[1]
            vep_output_file_path = tempfile.mkstemp()[1]

            vep_input_file = open(vep_input_file_path, 'w')
            vcf_stuff.write_sites_vcf(vep_input_file, variant_t_batch)
            vep_input_file.close()

            self._run_vep(vep_input_file_path, vep_output_file_path)

            with open(vep_output_file_path) as f:
                ret = list(parse_vep_annotations_from_vcf(f))

            os.remove(vep_input_file_path)
            os.remove(vep_output_file_path)

            return ret

        batch = []
        for variant_t in variant_t_list:
            batch.append(variant_t)
            if len(batch) == self._vep_batch_size:
                print "Running VEP on next {} variants, through {}".format(self._vep_batch_size, variant_t[0])
                annotations = process_batch(batch)
                for variant, annotation in annotations:
                    yield variant.unique_tuple(), annotation
                batch = []
        if len(batch) > 0:
            annotations = process_batch(batch)
            for variant, annotation in annotations:
                yield variant.unique_tuple(), annotation


def parse_vep_annotations_from_vcf(vcf_file_obj):
    """
    Iterate through the variants in a VEP annotated VCF, pull out annotation from CSQ field
    """

    r = vcf.VCFReader(vcf_file_obj)
    if "CSQ" not in r.infos:
        raise ValueError("CSQ field not found in %s header" % vcf_file_obj)
    csq_field_names = r.infos["CSQ"].desc.split("Format: ")[1].split("|")
    csq_field_names = map(lambda s: s.lower(), csq_field_names)

    total_sites_counter = 0
    missing_csq_counter = 0
    for vcf_row in r:
        vep_annotations = []
        total_sites_counter += 1
        if "CSQ" not in vcf_row.INFO:
            missing_csq_counter += 1
            if total_sites_counter > 10000 and missing_csq_counter / float(total_sites_counter) > 0.2:
                raise Exception("%d out of %d vcf rows processed so far are missing the CSQ INFO field. Something probably went wrong with VEP annotation." % (missing_csq_counter, total_sites_counter))
            else:
                continue  # Skip the occasional sites where, due to subsetting, the alt allele is *

        for i, per_transcript_csq_string in enumerate(vcf_row.INFO["CSQ"]):
            csq_values = per_transcript_csq_string.split('|')

            # sanity-check the csq_values
            if len(csq_values) != len(csq_field_names):
                raise ValueError("CSQ per-transcript string %s contains %s values instead of %s:\n%s" % (
                    i, len(csq_values), len(csq_field_names), per_transcript_csq_string))

            vep_annotation = dict(zip(csq_field_names, csq_values))
            vep_annotation['is_nmd'] = "NMD_transcript_variant" in csq_values
            # 2 kinds of 'nc_transcript_variant' label due to name change in Ensembl v77
            vep_annotation['is_nc'] = "nc_transcript_variant" in csq_values or "non_coding_transcript_variant" in csq_values

            variant_consequence_strings = vep_annotation["consequence"].split("&")
            vep_annotation["consequence"] = get_worst_vep_annotation(variant_consequence_strings)
            vep_annotations.append(vep_annotation)

        vcf_fields = [vcf_row.CHROM, vcf_row.POS, vcf_row.ID, vcf_row.REF, ",".join(map(str, vcf_row.ALT))]
        variant_objects = vcf_stuff.get_variants_from_vcf_fields(vcf_fields)
        for variant_obj in variant_objects:
            if variant_obj.alt == "*":
                #print("Skipping GATK3.4 * alt alleles: " + str(variant_obj.unique_tuple()))
                continue
            yield variant_obj, vep_annotations
    print("WARNING: %d out of %d sites were missing the CSQ field" % (missing_csq_counter, total_sites_counter))




def parse_csq_info(csq_string, csq_field_names):
    """
    Parses the CSQ string added by VEP to the VCF INFO field.
    (see http://useast.ensembl.org/info/docs/tools/vep/vep_formats.html#vcfout for details on the CSQ format)

    Args:
        csq_string: the string value of the CSQ key in the INFO value
        csq_field_names: list of strings representing names of the '|'-separated values in the CSQ field
    Generates:
        A dictionary for each transcript, where each dictionary contains csq_field_names mapped
        to their values in the give csq_string.
    """

    for i, per_transcript_csq_string in enumerate(csq_string.split(',')):

        csq_values = per_transcript_csq_string.split('|')

        # sanity-check the csq_values
        if len(csq_values) != len(csq_field_names):
            raise ValueError("CSQ per-transcript string %s contains %s values instead of %s:\n%s" % (
                i, len(csq_values), len(csq_field_names), per_transcript_csq_string))

        d = dict(zip(csq_field_names, csq_values))
        d['is_nmd'] = "NMD_transcript_variant" in csq_values
        # 2 kinds of 'nc_transcript_variant' label due to name change in Ensembl v77
        d['is_nc'] = "nc_transcript_variant" in csq_values or "non_coding_transcript_variant" in csq_values

        variant_consequence_strings = d["consequence"].split("&")
        d["consequence"] = get_worst_vep_annotation(variant_consequence_strings)

        yield d


def get_worst_vep_annotation(vep_variant_consequence_strings):
    """
    Args:
        vep_variant_consequence_strings: A list of VEP variant consequence strings
        (eg. ['missense_variant', 'intergenic'])
    Returns:
        The string from the list which is considered the worst effect in terms of severity.
    """

    vep_variant_severity_indexes = []
    for s in set(vep_variant_consequence_strings):
        try:
            vep_variant_severity_indexes.append(
                SO_SEVERITY_ORDER.index(s))
        except ValueError:
            raise ValueError("Unexpected consequence string: " + s)

    worst_i = min(vep_variant_severity_indexes)
    return SO_SEVERITY_ORDER[worst_i]


def get_csq_fields_from_vcf_desc(csq_desc):
    """
    Runs a regex on meta line and gives back list of CSQ fields
    """
    search = re.search('Format: ([\w|\|]+)', csq_desc)
    fields = search.group(1).split('|') if search.group(1) else []
    return [f.lower() for f in fields]



def get_worst_vep_annotation_index(transcript_annotations, gene_id=None):
    """
    Returns (zero-based) index of the VEP annotation with the worst consequence.

    Args:
        transcript_annotations: a list where each element represents VEP annotations
            for a different transcript (parsed from a VCF record's CSQ field).
        gene_id: if specified, only annotations with this gene_id will be
            considered. This is useful when the transcript_annotations list
            contains transcripts from more than one gene.
    """

    if not transcript_annotations:
        raise ValueError("transcript_annotations is empty")

    annotations = [(i, ta) for i, ta in enumerate(transcript_annotations)]

    # filter by gene_id
    if gene_id is not None:
        annotations = [(i, ta) for i, ta in annotations if ta['gene'] == gene_id]
        if not annotations:
            raise ValueError("None of the transcripts in %s have gene_id: %s" % (transcript_annotations, gene_id))

    # find the transcript(s) affected with the worst severity
    worst_severity = 10**9   # lower numbers are worse severity
    worst_severity_annotations = []  # a list of worst-severity transcripts
    for i, transcript_annotation in annotations:
        try:
            severity_scale = SO_SEVERITY_ORDER.index(
                transcript_annotation['consequence'])
        except ValueError as e:
            raise ValueError("Unexpected VEP consequence: %s: %s" % (
                transcript_annotation['consequence'], e))

        # hack: this is to deprioritize noncoding and nonsense mediated decay transcripts
        if transcript_annotation['is_nc']:
            severity_scale += NUM_SO_TERMS
        if transcript_annotation['is_nmd']:
            severity_scale += 2*NUM_SO_TERMS

        if severity_scale <= worst_severity:
            if severity_scale < worst_severity:
                worst_severity_annotations = []
                worst_severity = severity_scale

            worst_severity_annotations.append((i, transcript_annotation))

    # if multiple transcripts have the same worst severity, chose the canonical transcript
    for i, transcript_annotation in worst_severity_annotations:
        if transcript_annotation['canonical']:
            worst_severity_annotation_index = i
            break
    else:
        # otherwise, sort transcripts alphabetically by transcript id and return the 1st one
        worst_severity_annotations.sort(key=lambda x: x[1]['feature'])
        worst_severity_annotation_index, _ = worst_severity_annotations[0]

    return worst_severity_annotation_index


def get_gene_ids(vep_annotation):
    """
    Gets the set of gene ids this variant is attached to
    Empty list if no annotations
    """
    return list(set([annotation['gene'] for annotation in vep_annotation]))


def is_coding_annotation(annotation):
    """
    Does this annotation impact coding?
    """
    return SO_SEVERITY_ORDER_POS[annotation['consequence']] <= CODING_POS_CUTOFF


def get_coding_gene_ids(vep_annotation):
    """
    Set of gene IDs that this is a coding variant for
    Still included even if is_nmd or is_nc
    Empty list if no annotations
    """
    return list(set([annotation['gene'] for annotation in vep_annotation if is_coding_annotation(annotation) ]))


