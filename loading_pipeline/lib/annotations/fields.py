from collections.abc import Callable
from typing import Any

import hail as hl


def get_fields(
    t: hl.Table | hl.MatrixTable,
    fns: list[Callable[..., hl.Expression]],
    **kwargs: Any,
) -> dict[str, hl.Expression]:
    return {fn.__name__: fn(t, **kwargs) for fn in fns}
