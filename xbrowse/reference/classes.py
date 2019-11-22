from collections import namedtuple

# TODO: start using this in coverage
GenomeRegion = namedtuple('GenomeRegion', ['xstart', 'xend'])

CodingRegion = namedtuple('CodingRegion', ['gene_id', 'index_in_gene', 'xstart', 'xstop'])