import os
import re
import sh
import tempfile

from xbrowse import vcf_stuff

SO_SEVERITY_ORDER = [
    'transcript_ablation',
    'splice_donor_variant',
    "splice_acceptor_variant",
    'stop_gained',
    'frameshift_variant',
    'stop_lost',
    'initiator_codon_variant',
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
            "--everything",  # http://useast.ensembl.org/info/docs/tools/vep/script/vep_options.html#opt_everything
            "--vcf",
            "--fasta", os.path.join(self._vep_cache_dir,
                "homo_sapiens/78_GRCh37/Homo_sapiens.GRCh37.75.dna.primary_assembly.fa"),
            "--filter", "no_intergenic_variant,no_feature_truncation,no_feature_elongation,"
                "no_regulatory_region_variant,no_regulatory_region_amplification,no_regulatory_region_ablation,"
                "no_downstream_gene_variant,no_upstream_gene_variant,no_intron_variant,"
                "no_non_coding_transcript_variant",
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
    header_info = {}
    csq_field_names = None
    for variant in vcf_stuff.iterate_vcf(vcf_file_obj, meta_fields=['CSQ'], header_info=header_info):
        if csq_field_names is None:
            csq_field_names = get_csq_fields_from_vcf_desc(header_info['CSQ'].desc)

        vep_annotation = list(parse_csq_info(variant.extras['CSQ'], csq_field_names))
        yield variant, vep_annotation

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
        d['is_nc'] = "nc_transcript_variant" in csq_values

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



def get_worst_vep_annotation_index(vep_annotation, gene_id=None):
    """
    Returns index of which VEP annotation is worst (zero-indexed)
    Exception if no vep annotation for some reason

    if you want the index of worst annotation for a given gene, pass gene_id
    gene_id is None implies the worst global annotation

    """

    num_annotations = len(vep_annotation)
    if num_annotations == 0:
        print 'Warning: no VEP annnotation'
        return None

    worst_value = 1000
    worst_index = -1
    for i in range(num_annotations):

        if gene_id and vep_annotation[i]['gene'] != gene_id: continue

        annot = vep_annotation[i]['consequence']

        try:
            pos = SO_SEVERITY_ORDER.index(annot)

            # hack: this is to deprioritize noncoding and nonsense mediated decay transcripts
            if vep_annotation[i]['is_nc']:
                pos += NUM_SO_TERMS
            if vep_annotation[i]['is_nmd']:
                pos += 2*NUM_SO_TERMS

        except ValueError:
            print 'Warning: no VEP ordering for %s' % annot
            return None

        if pos < worst_value:
            worst_index = i
            worst_value = pos

    return worst_index


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


