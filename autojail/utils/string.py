def remove_prefix(text: str, prefix: str) -> str:
    """Remove prefix from text if prefix exists"""
    return text[text.startswith(prefix) and len(prefix) :]


def pprint_tree(node, file=None, _prefix="", _last=True):
    """pretty print a tree like datastructure"""
    # FIXME: make output method configurable
    print(
        _prefix, "`- " if _last else "|- ", node.value, sep="", file=file
    )  # noqa
    _prefix += "   " if _last else "|  "
    child_count = len(node.children)
    for i, child in enumerate(node.children):
        _last = i == (child_count - 1)
        pprint_tree(child, file, _prefix, _last)
