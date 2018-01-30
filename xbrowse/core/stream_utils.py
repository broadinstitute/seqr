"""
Many of the lookups in xbrowse are returned as streams,
Streams themselves can be operated on with these utils
"""

import Queue
import heapq
import itertools


def combine_variant_streams(stream_list):
    """
    Combines an arbitraty number of variant streams into a single stream, in genomic order
    Each input stream must be in genomic order
    """

    # priority queue stores tuples of (genomic order, stream index, variant)
    # TODO: Queue or heapq?
    variant_queue = Queue.PriorityQueue()

    for stream_index, stream in enumerate(stream_list):

        try:
            variant = stream.next()
            variant_queue.put((variant.xpos, stream_index, variant))
        except StopIteration:
            pass

    while True:

        if variant_queue.empty():
            raise StopIteration
        else:
            pos, stream_index, variant = variant_queue.get()

        try:
            next_variant = stream_list[stream_index].next()
            variant_queue.put((next_variant.xpos, stream_index, next_variant))
        except StopIteration:
            pass

        yield variant

def unique_variant_stream(stream):
    """
    Remove duplicate variants from a stream.
    To be "duplicate", variant need only the same single_position, ref, and alt -- so genotypes ignored
    Should only use this streams from the same data source
    """
    raise NotImplementedError


def variant_stream_to_gene_stream(stream, reference):
    """
    Turns a variant stream into a stream of tuples (gene, variant_list)
    Allows multiple gene annotations, but requires gene annotations to be contiguous
    TODO: should switch to generic regions instead of gene
    TODO: check this for corner cases - what if variant / gene order is awkward?

    Algorithm: look through genome, keep track of which genes you are currently reading (current_genes)
    For each variant:
    -- get list of genes
    -- add variant to each in current_genes
    -- if any genes didn't get a variant added, yield them

    """
    current_genes = {}
    while True:
        try:
            variant = stream.next()
        except StopIteration:
            for gene, variants in current_genes.items():
                yield (gene, variants)
            raise StopIteration

        genes = variant.gene_ids
        for gene in genes:
            if gene == '':
                continue
            if not gene in current_genes:
                current_genes[gene] = []
            current_genes[gene].append(variant)


# TODO: tests for ref/alt corner cases
# TODO: make public
def _combine_variant_lists(list_of_lists):
    """
    Combine variant lists in memory into genomic order
    Currently all in memory; no streams
    """
    return sorted(
        [v for l in list_of_lists for v in l],
        key=lambda v: (v.xpos, v.ref, v.alt)
    )


def _uniqify_variant_list(variant_list):
    """
    Remove duplicats from a sorted variant list
    """
    def r(x, y):
        if len(x) == 0:
            x.append(y)
            return x
        elif x[-1] == y:
            return x
        else:
            x.append(y)
            return x
    sorted_variant_list = _sort_variant_list(variant_list)
    return reduce(r, sorted_variant_list, [])


def _sort_variant_list(variant_list):
    return sorted(variant_list, key=lambda v: (v.xpos, v.ref, v.alt))


def combine_gene_streams(stream_list, reference):
    """
    Analagous to combine_variant_streams;
    combines an arbitraty number of gene streams into a single stream, in genomic order
    Genes are combined - variant lists are merged; but
    does *not* eliminate duplicate variants...see remove_duplicate_variants_from_gene_stream

    TODO: results not necessarily sorted, because no way to access gene coords.
    Need to add dependency on reference

    Algorithm (TODO: switch to priority queue after we get gene order)
    -- Get a gene from all streams
    -- Combine genes that need to be combined
    -- Return each gene
    """

    next_genes = {}  # map from gene -> list of variant lists
    gene_queue = []  # priority queue for identifying next closest gene.
                     # Elements are tuples of (gene position, gene name, stream index)

    def add_gene(stream_index):
        gene, variant_list = stream_list[stream_index].next()
        if gene in next_genes:
            next_genes[gene].append(variant_list)
            add_gene(stream_index)
        else:
            next_genes[gene] = [variant_list, ]
            heapq.heappush(gene_queue, (reference.get_gene_bounds(gene), gene, stream_index))

    for i, stream in enumerate(stream_list):
        try:
            add_gene(i)
        except StopIteration:
            pass

    while True:

        if len(next_genes) == 0:
            raise StopIteration

        position, gene_name, stream_index = heapq.heappop(gene_queue)
        try:
            add_gene(stream_index)
        except StopIteration:
            pass

        list_of_lists = next_genes[gene_name]
        del next_genes[gene_name]  # only need to delete from next_genes; heappop deletes from other

        yield (gene_name, _combine_variant_lists(list_of_lists))


def remove_duplicate_variants_from_gene_stream(gene_stream):
    """
    Sorry for the long title, hopefully self explanatory though :)
    """
    for gene, variant_list in gene_stream:

        # TODO: better key function
        yield (gene, [list(v)[0] for _, v in itertools.groupby(variant_list, key=lambda variant: str(variant.xpos) + variant.ref + variant.alt) ])


def gene_stream_to_variant_stream(gene_stream, reference):
    """
    TODO: does not guarantee variants are in order if genes overlap
    TODO: remove duplicate variants
    """
    variant_queue = []
    pending_variants = set()

    # gets tuple for random access
    def get_tuple(variant):
        return variant.xpos, variant.ref, variant.alt

    # Flush all variants that end *before* pos
    def flush_to(pos):
        while True:
            _next = heapq.nsmallest(1, variant_queue)
            if len(_next) == 0:
                break
            next_variant = _next[0][1]

            if next_variant.xposx < pos:
                heapq.heappop(variant_queue)
                pending_variants.discard(get_tuple(next_variant))
                yield next_variant
            else:
                break

    for gene_id, variant_list in gene_stream:
        for variant in variant_list:
            vartuple = get_tuple(variant)
            if vartuple not in pending_variants:
                pending_variants.add(vartuple)
                heapq.heappush(variant_queue, (variant.xpos, variant))

        start_of_gene = reference.get_gene_bounds(gene_id)
        if start_of_gene is not None:
            flush_to(start_of_gene[0])

    for item in flush_to(25e9):
        yield item
