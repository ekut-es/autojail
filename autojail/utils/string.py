def remove_prefix(text: str, prefix: str) -> str:
    """Remove prefix from text if prefix exists"""
    return text[text.startswith(prefix) and len(prefix) :]
