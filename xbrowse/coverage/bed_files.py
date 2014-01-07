import constants
from .classes import CoverageInterval

from xbrowse import genomeloc


def iterate_coverage_bed_file(bed_file):
    for line in bed_file:
        fields = line.strip().split('\t')
        chr = 'chr' + fields[0]
        start = int(fields[1])
        end = int(fields[2])-1
        xstart = genomeloc.get_single_location(chr, start)
        xstop = genomeloc.get_single_location(chr, end)
        coverage = constants.COVERAGE_TAG_MAP[fields[3]]

        yield CoverageInterval(xstart=xstart, xstop=xstop, coverage=coverage)