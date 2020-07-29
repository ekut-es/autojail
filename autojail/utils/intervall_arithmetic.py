from typing import Any, Tuple


def get_overlap(a: Tuple[Any, Any], b: Tuple[Any, Any]) -> int:
    """Calculate the overlab between the two open intervalls [a0, a1[ and [b0, b1["""
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))
