def constrain(
    number: int | float,
    lower_bound: int | float,
    upper_bound: int | float,
) -> int:
    if lower_bound > upper_bound:
        msg = 'Lower bound should be less than or equal to upper bound'
        raise ValueError(msg)
    return max(lower_bound, min(number, upper_bound))
