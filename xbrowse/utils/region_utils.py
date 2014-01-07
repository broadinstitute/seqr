
def flatten_region_list(region_list):
    """
    Flatten a region list if they overlap
    region_list is a list of (start, end) tuples
    Returns a new list of region tuples
    """
    if len(region_list) == 0:
        return []

    flattened_list = []

    current_region = region_list[0]
    for start, end in region_list[1:]:
        if start <= current_region[1]:
            current_region = (current_region[0], end)
        else:
            flattened_list.append(current_region)
            current_region = (start, end)
    flattened_list.append(current_region)
    return flattened_list

def get_interval_overlap(region1, region2):
    """
    What is the (inclusive) overlap between these two regions?
    Return (xstart, xstop) tuple that defines the overlap, or None if no overlap
    """
    if region1[0] > region2[1]:
        return None
    if region1[1] < region2[0]:
        return None

    # region1 contains region2
    if region1[0] <= region2[0] and region1[1] >= region2[1]:
        return region2

    # region2 contains region1
    elif region1[0] >= region2[0] and region1[1] <= region2[1]:
        return region1

    # region1 overlaps start of region2
    elif region1[1] < region2[1]:
        return region2[0], region1[1]

    # region1 overlaps end of region2
    else:
        return region1[0], region2[1]
