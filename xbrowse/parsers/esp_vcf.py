from xbrowse import vcf_stuff

def get_variants_from_esp_file(file_like_object):
    """
    file_like_object is an ESP-style VCF file
    This could be called 23 times, one for each file, or just once after running vcf-merge
    Return a stream of variants with the following structure:
    {
        'xpos': long int
        'ref': str,
        'alt': alt,
        'esp_ea': float - aaf in european americans
        'esp_aa': float - aaf in african americans
    }
    Note that ref and alt are *not* currently reduced by xbrowse
    """

    ac_meta_fields = ['EA_AC', 'AA_AC']
    for variant in vcf_stuff.iterate_vcf(file_like_object, meta_fields=ac_meta_fields, vcf_row_info=True):

        v = {
            'xpos': variant.xpos,
            'ref': variant.ref,
            'alt': variant.alt,
        }
        ea_counts = [int(c) for c in variant.extras['EA_AC'].split(',')]
        aa_counts = [int(c) for c in variant.extras['AA_AC'].split(',')]

        ea_total = sum(ea_counts)
        aa_total = sum(aa_counts)

        # note that allele counts in VCF are alt1,alt2,ref.
        # ...dumb
        ea_thisallele = ea_counts[variant.extras['vcf_row_info']['alt_allele_pos']]
        aa_thisallele = aa_counts[variant.extras['vcf_row_info']['alt_allele_pos']]

        v['esp_ea'] = float(ea_thisallele) / ea_total
        v['esp_aa'] = float(aa_thisallele) / aa_total

        yield v