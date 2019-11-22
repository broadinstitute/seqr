import bed_files
from classes import CoverageInterval

from xbrowse.utils import region_utils


def fill_in_missing_intervals(coding_region, coverage_interval_list):
    """
    coverage_interval_list is an ordered list of coverage intervals that might not be comprehensive
    fill in the missing spaces (ie. any space between intervals A and B where a['xstop'] +1 < b['xstart']
    return list of CoverageInterval instances that is comprehensive
    """
    full_intervals = []
    if len(coverage_interval_list) == 0:
        return [CoverageInterval(coding_region.xstart, coding_region.xstop, 'low_coverage'),]
    if coverage_interval_list[0].xstart > coding_region.xstart:
        full_intervals.append(CoverageInterval(
            xstart=coding_region.xstart,
            xstop=coverage_interval_list[0].xstart-1,
            coverage='low_coverage'
        ))
    # for each coverage_interval (besides the final one),
    # make sure the end of this interval is 1 minus start of the next
    # if not, fill it in
    for i, coverage_interval in enumerate(coverage_interval_list):
        full_intervals.append(coverage_interval)
        if i == len(coverage_interval_list)-1:
            if coverage_interval.xstop < coding_region.xstop-1:
                full_intervals.append(CoverageInterval(coverage_interval.xstop+1, coding_region.xstop, 'low_coverage'))
            continue
        if coverage_interval.xstop < coverage_interval_list[i+1].xstart-1:
            full_intervals.append(CoverageInterval(
                xstart=coverage_interval.xstart+1,
                xstop=coverage_interval_list[i+1].xstart-1,
                coverage='low_coverage'
            ))
    return full_intervals


def get_totals_for_coverage_interval_list(coverage_interval_list):
    """
    dict of coverage_key -> num_bases across this interval list
    assumed that coverage_interval_list does not have breaks
    """
    ret = {
        'callable': 0,
        'low_coverage': 0,
        'poor_mapping': 0
    }
    for coverage_interval in coverage_interval_list:
        ret[coverage_interval.coverage] += (coverage_interval.xstop-coverage_interval.xstart+1)
    ret['ratio_callable'] = ret['callable'] / float(ret['callable']+ret['low_coverage']+ret['poor_mapping'])
    return ret

def map_coverage_onto_coding_regions(coverages, coding_regions):
    """
    Get the total coverage for each exon
    coding_regions is an iterator over oredered CodingRegion instances
    coverages is an iterator over CoverageInterval instances
    coding regions can overlap; coverages cannot
    coverages don't need to be continuous; missing regions are assumed to be low coverage
    returns iterator of dictionaries with keys:
    - coding_region
    - totals: dict of callable, low_coverage, poor_mapping
    - intervals: list of CoverageIntervals - no missing spaces
    """

    # list of (coding_region, coverage_interval_list) tuples
    current_coding_regions = []

    last_coding_region_c = {'c': None} # no write closures in python 2

    def move_needle_to(xpos):
        """
        Moving needle to xpos means that all exons that are before or overlapping xpos have been "processed" -
        meaning appended to current_cdss
        """
        while True:
            last_cds = last_coding_region_c['c']
            if last_cds is None:
                try:
                    last_coding_region_c['c'] = coding_regions.next()
                    continue
                except StopIteration:
                    break

            # now let's see if last_exon should be added to current_exons
            if last_cds.xstart > xpos:
                break
            current_coding_regions.append((last_cds, []))
            last_coding_region_c['c'] = None

    def pop_all_before(xpos):
        """
        Yield all cds from current_exons that are less than xpos
        Before we can yield, must do the following post-processing:
        - fill in empty regions (with mock low_coverage interval)
        - calculate totals for region
        """
        ret = []
        while True:
            if len(current_coding_regions) == 0:
                break
            if current_coding_regions[0][0].xstop < xpos:

                coverage_interval_list = current_coding_regions[0][1]
                full_coverage_interval_list = fill_in_missing_intervals(
                    current_coding_regions[0][0],
                    coverage_interval_list
                )

                doc = {
                    'coding_region': current_coding_regions[0][0],
                    'totals': get_totals_for_coverage_interval_list(full_coverage_interval_list),
                    'coverage_list': full_coverage_interval_list
                }

                ret.append(doc)
                current_coding_regions.pop(0)

            else:
                break
        return ret

    move_needle_to(0)
    for coverage in coverages:
        move_needle_to(coverage.xstop)
        for coding_region, coverage_interval_list in current_coding_regions:
            coding_region_t = (coding_region.xstart, coding_region.xstop)
            coverage_interval_t = (coverage.xstart, coverage.xstop)
            overlap = region_utils.get_interval_overlap(coding_region_t, coverage_interval_t)
            if overlap:
                coverage_interval_list.append(CoverageInterval(
                    xstart=overlap[0],
                    xstop=overlap[1],
                    coverage=coverage.coverage)
                )
        for item in pop_all_before(coverage.xstart):
            yield item
    move_needle_to(1e11)
    for item in pop_all_before(1e11):
        yield item


def iterate_coding_region_coverages(coverage_file, coding_regions):
    """
    Iterate through dicts with keys:
    - coding_region: CodingRegion instance
    - totals: dict of coverage -> sum across this region
    - coverage_list: list of CoverageInterval classes
    """
    coverages = bed_files.iterate_coverage_bed_file(coverage_file)
    return map_coverage_onto_coding_regions(coverages, coding_regions)


def get_totals_for_coding_region_list(coverage_spec_list):
    """
    Cumulative coverage across an (ordered) set of coverage specs
    Return dict of:
    - callable
    - low_coverage
    - poor_mapping
    - num_complete_regions
    - num_incomplete_regions
    """
    ret = {
        'callable': 0,
        'low_coverage': 0,
        'poor_mapping': 0,
        'num_complete_regions': 0,
        'num_incomplete_regions': 0,
    }
    for coverage_spec in coverage_spec_list:
        ret['callable'] += coverage_spec['totals']['callable']
        ret['low_coverage'] += coverage_spec['totals']['low_coverage']
        ret['poor_mapping'] += coverage_spec['totals']['poor_mapping']
        if coverage_spec['totals']['low_coverage'] + coverage_spec['totals']['poor_mapping'] == 0:
            ret['num_complete_regions'] += 1
        else:
            ret['num_incomplete_regions'] += 1
    try:
        ret['ratio_callable'] = ret['callable']/float(ret['callable']+ret['low_coverage']+ret['poor_mapping'])
    except ZeroDivisionError:
        ret['ratio_callable'] = 0
    return ret