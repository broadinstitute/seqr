import hail as hl


def sorted_hl_struct(s: hl.StructExpression) -> hl.StructExpression:
    if not isinstance(s, hl.StructExpression):
        return s
    return s.select(**{k: sorted_hl_struct(s[k]) for k in sorted(s)})
