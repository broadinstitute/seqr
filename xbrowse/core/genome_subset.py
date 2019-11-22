from xbrowse.core import genomeloc
#import banyan


class GenomeSubsetFilter():
    """
    This class represents a subset of nonoverlapping intervals in the genome
    It is used for filtering variants, and is most commonly used to represent an exome target -
    but can be used for many other purposes
    TODO: right now this assumes variants are 1 base long - need to expand to cover all those corner cases
    """

    def __init__(self, intervals):
        """
        Intervals is an iter of (xstart, xend) tuples
        """
        if len(intervals) == 0:
            raise Exception("Intervals cannot have length 0")
        self.intervals = intervals
        # removing because banyan was causing install problems and we don't actually use this
        #self.interval_tree = banyan.SortedSet(intervals, updator=banyan.OverlappingIntervalsUpdator)

    def filter_variant_list(self, variant_t_list):
        """
        Returns:
            List of (variant, True/False) tuples, indicating whether variant falls in this GenomeSubset
        """
        ret = []

        interval_i = iter(self.intervals)
        next_interval = interval_i.next()

        for variant_t in variant_t_list:
            # if variant is past target, get new target
            try:
                while variant_t[0] > next_interval[1]:
                    next_interval = interval_i.next()
            except StopIteration:
                pass
            if next_interval[0] <= variant_t[0] <= next_interval[1]:
                ret.append((variant_t, True))
            else:
                ret.append((variant_t, False))

        return ret


def create_genome_subset_from_interval_list(interval_list_file):
    """
    Creates a genome subset from interval list file
    This is a file with cols chr, start, stop, strand, name
    Strand and name are ignored, and actually it could have extra cols too and won't complain
    Coordinates are 1-indexed and inclusive
    """
    intervals = []
    for line in interval_list_file:
        fields = line.strip('\n').split('\t')
        chrom = 'chr'+fields[0]
        start = int(fields[1])
        end = int(fields[2])
        intervals.append((genomeloc.get_single_location(chrom, start), genomeloc.get_single_location(chrom, end)))
    return GenomeSubsetFilter(intervals)