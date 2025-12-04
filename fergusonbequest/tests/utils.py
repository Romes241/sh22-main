"""Shared test helpers for fergusonbequest tests.

Provides simple unique identifier generators used across tests so values
are consistent and easy to change in one place.
"""

from django.utils.crypto import get_random_string


def unique_email(prefix: str = "user", length: int = 8) -> str:
    """Return a short unique email for tests.

    Args:
        prefix: optional prefix for the local-part (default: 'user')
        length: number of random characters to append (default: 8)

    Returns:
        A string like "{prefix}-{random}@example.com" safe for tests.
    """
    return f"{prefix}-{get_random_string(length)}@example.com"


def unique_username(prefix: str = "user", length: int = 6) -> str:
    """Return a short unique username for tests.

    Args:
        prefix: optional prefix (default: 'user')
        length: number of random characters to append (default: 6)

    Returns:
        A string like "{prefix}_{random}" suitable for username fields.
    """
    return f"{prefix}_{get_random_string(length)}"
