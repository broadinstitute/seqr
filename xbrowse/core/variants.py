from collections import namedtuple
import copy

from xbrowse.core import genomeloc

#
# This is a single genotype.
# No real notion of a default value; all fields are None if N/A
# Individual ID is not actually stored here; as you'll see from the field defs,
# a genotype out of context doesn't really make any sense.
#
from xbrowse.utils.basic_utils import _encode_name, _decode_name

Genotype = namedtuple('Genotype', [
    'alleles',  # tuple;
    'gq',  # float; value of the GQ field in VCF
    'num_alt',  # int; number of alternate alleles. 1 indicates heterozygous, 2 hom/alt.
    'filter',  # string; value of FILTER field, in the VCF row this genotype was taken from
    'ab',  # float; proportion of non-reference reads
    'extras',  # dict; other genotype meta information stored here
])


def genotype_dict(genotype):
    #  Using namedtuples _asdict method is very slow, so so an explicit dict construction instead
    # See https://stackoverflow.com/questions/47432731/why-namedtuple-as-dict-is-slower-than-conversion-using-dict
    return {
        'alleles': genotype.alleles,
        'gq':  genotype.gq,
        'num_alt':  genotype.num_alt,
        'filter':  genotype.filter,
        'ab':  genotype.ab,
        'extras': genotype.extras,
    }


class Variant():
    """
    This is a single variant. It optionally contains genotypes.

    It is dataset-agnostic - genotypes can be constructed from multiple callsets, or the same - up to client
    However, can only contain one genotype for each individual

    Currently, a variant is defined positionally by (xpos, ref, alt) tuple,
    where ref and alt are distinct allele strings
    This means that a tandem repeat with 5-10 repeats is coded as 6 separate variants
    Obviously this needs to change, but no hard plans yet.

    Coordinates are similar to VCF - one-based, and includes preceding base
    However, they are stored by "xpos" - a one dimensional coordinate index with a two way map to a (chr, pos) tuple
    See genomeloc.py for more details
    """

    def __init__(self, xpos, ref, alt):
        self.xpos = xpos
        self.ref = ref
        self.alt = alt

        # TODO: should be implemented in genomeloc.py
        self.xposx = xpos
        if len(ref) == 1 and len(alt) > 1:  # insertion
            self.xposx += len(alt) - 1
        elif len(ref) > 1 and len(alt) == 1:  # deletion
            self.xposx -= 1
        elif len(ref) > 1 and len(alt) > 1:  # multi base sub
            self.xposx += len(alt) - 1
        chrom, pos = genomeloc.get_chr_pos(self.xpos)
        self.chr = chrom
        self.pos = pos
        self.pos_end = self.xposx % 1e9

        # TODO: feels like this should be an ordered dict
        self.genotypes = {}
        self.extras = {}
        self.annotation = None
        self.gene_ids = []
        self.coding_gene_ids = []

        self.vcf_id = None
        self.vartype = 'snp' if len(ref) == 1 and len(alt) == 1 else 'indel'

    def toJSON(self, encode_indiv_id=False):
        return {
            'xpos': self.xpos,
            'xposx': self.xposx,
            'chr': self.chr,
            'pos': self.pos,
            'pos_end': self.pos_end,
            'ref': self.ref,
            'alt': self.alt,
            'genotypes': {
                _encode_name(indiv_id) if encode_indiv_id else indiv_id: genotype_dict(genotype) for indiv_id, genotype in self.get_genotypes()
            },
            'extras': self.extras,
            'annotation': self.annotation,
            'gene_ids': self.gene_ids,
            'coding_gene_ids': self.coding_gene_ids,
            'vcf_id': self.vcf_id,
            'vartype': self.vartype,
        }

    @staticmethod
    def fromJSON(variant_dict):
        variant = Variant(variant_dict['xpos'], variant_dict['ref'], variant_dict['alt'])

        for indiv_id, genotype_dict in variant_dict['genotypes'].items():
            alleles = genotype_dict.get('alleles')
            gq = genotype_dict.get('gq')
            num_alt = genotype_dict.get('num_alt')
            filt = genotype_dict.get('filter')
            ab = genotype_dict.get('ab')
            extras = genotype_dict.get('extras')
            
            variant.genotypes[_decode_name(indiv_id)] = Genotype(alleles=alleles, gq=gq, num_alt=num_alt, filter=filt, ab=ab, extras=extras)
            
        variant.extras = variant_dict.get('extras')
        variant.annotation = variant_dict.get('annotation')
        variant.gene_ids = variant_dict.get('gene_ids', [])
        variant.coding_gene_ids = variant_dict.get('coding_gene_ids', [])
        variant.vcf_id = variant_dict.get('vcf_id')
        variant.vartype = variant_dict.get('vartype')
        return variant

    def __str__(self):
        return "%s-%s-%s-%s" % (self.chr, self.pos, self.ref, self.alt)

    def unique_tuple(self):
        return self.xpos, self.ref, self.alt

    def get_genotype(self, indiv_id):
        return self.genotypes.get(indiv_id)

    def get_genotypes(self):
        return self.genotypes.items()

    def num_genotypes(self):
        return len(self.genotypes)

    def make_copy(self, restrict_to_genotypes=None):
        """
        Copy this variant, like a copy constructor
        """
        new_variant = Variant(self.xpos, self.ref, self.alt)

        if restrict_to_genotypes is None:
            new_variant.genotypes = self.genotypes
        else:
            g = {}
            for indiv_id in restrict_to_genotypes:
                g[indiv_id] = self.get_genotype(indiv_id)
            new_variant.genotypes = g

        new_variant.extras = copy.copy(self.extras)
        new_variant.annotation = self.annotation
        new_variant.gene_ids = self.gene_ids
        new_variant.coding_gene_ids = self.coding_gene_ids
        new_variant.vcf_id = self.vcf_id
        new_variant.vartype = self.vartype

        return new_variant

    def get_extra(self, key):
        return self.extras.get(key)

    def set_extra(self, key, val):
        self.extras[key] = val


