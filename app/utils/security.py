from urllib.parse import urlsplit


def is_safe_local_redirect(target):
    """Return True only for same-origin application-relative redirect paths."""
    if not target or not isinstance(target, str):
        return False
    target = target.strip()
    if not target.startswith('/') or target.startswith('//'):
        return False
    parsed = urlsplit(target)
    return not parsed.scheme and not parsed.netloc
