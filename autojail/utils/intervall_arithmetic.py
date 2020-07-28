from typing import Tuple


def get_overlap(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Calculate the overlab between the two open intervalls [a0, a1[ and [b0, b1["""
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))
