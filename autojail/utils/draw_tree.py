from itertools import chain, repeat, starmap
from operator import add


def draw_tree(trees, nest=lambda x: x.children):
    """ASCII diagram of a tree."""
    res = []
    for tree in trees:
        res += draw_node(tree, nest)
    return "\n".join(res)


def draw_node(node, nest):
    """List of the lines of an ASCII
       diagram of a tree."""

    def shift(first, other, xs):
        return list(
            starmap(add, zip(chain([first], repeat(other, len(xs) - 1)), xs))
        )

    def draw_sub_trees(xs):
        return (
            (
                (
                    shift("├─ ", "│  ", draw_node(xs[0], nest))
                    + draw_sub_trees(xs[1:])
                )
                if 1 < len(xs)
                else shift("└─ ", "   ", draw_node(xs[0], nest))
            )
            if xs
            else []
        )

    return (str(node)).splitlines() + (draw_sub_trees(nest(node)))
