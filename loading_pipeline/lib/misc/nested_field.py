import hail as hl


def parse_nested_field(t: hl.MatrixTable | hl.Table, fields: str):
    expression = t
    # Behavior here allows only a single nested field.
    # Additional nesting is considered to be part of the
    # name of the field. e.g. `gnomadv4.1_AF`.
    for field in fields.split('.', maxsplit=1):
        # Select from multi-allelic list.
        if field.endswith('#'):
            expression = expression[field[:-1]][
                (t.a_index if hasattr(t, 'a_index') else 1) - 1
            ]
        else:
            expression = expression[field]
    return expression
