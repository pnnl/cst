"""
Validation utilities for data management components.

@author Nathan Gray
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Custom exception for validation errors."""

    pass


def validate_name(name: str, context: str = "name", max_length: int = 255) -> None:
    """
    Validate that a name is safe for filesystem and database use.

    Args:
        name (str): Name to validate
        context (str): Context for error messages (e.g., "federation", "scenario")
        max_length (int): Maximum allowed length

    Raises:
        ValidationError: If name is invalid

    Returns:
        None
    """
    if not name:
        raise ValidationError(f"{context.title()} name cannot be empty")

    if len(name) > max_length:
        raise ValidationError(
            f"{context.title()} name too long (>{max_length} chars): {name[:50]}..."
        )

    # Check for filesystem/database unsafe characters
    if re.search(r'[<>:"\\|?*\x00-\x1f]', name):
        raise ValidationError(
            f"{context.title()} name contains invalid characters: {name}"
        )

    # Check for reserved names (Windows + common reserved terms)
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{p}{i}" for p in ["COM", "LPT"] for i in range(1, 10)
    }
    if name.upper() in reserved:
        raise ValidationError(f"{context.title()} name is reserved: {name}")

    # Check for problematic start/end characters
    if name.startswith((" ", ".", "-")) or name.endswith((" ", ".", "-")):
        raise ValidationError(
            f"{context.title()} name has invalid format (starts/ends with space, dot, or dash): {name}"
        )


def validate_database_identifier(
    name: str, context: str = "identifier", max_length: int = 63
) -> None:
    """
    Validate that a name is safe for use as database identifier (table, schema, etc.).

    Args:
        name (str): Identifier to validate
        context (str): Context for error messages
        max_length (int): Maximum allowed length (PostgreSQL limit is 63)

    Raises:
        ValidationError: If identifier is invalid

    Returns:
        None
    """
    if not name:
        raise ValidationError(f"{context.title()} cannot be empty")

    if len(name) > max_length:
        raise ValidationError(
            f"{context.title()} too long (>{max_length} chars): {name[:30]}..."
        )

    # Database identifier rules: start with letter/underscore, contain letters/digits/underscores
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValidationError(
            f"{context.title()} must start with letter/underscore and contain only letters, digits, underscores: {name}"
        )

    # Check for SQL reserved words (basic check)
    reserved = {
        "user",
        "table",
        "column",
        "index",
        "constraint",
        "database",
        "schema",
        "select",
        "insert",
        "update",
        "delete",
        "create",
        "drop",
        "alter",
        "where",
        "from",
        "join",
        "group",
        "order",
        "having",
        "limit",
    }
    if name.lower() in reserved:
        raise ValidationError(f"{context.title()} is a reserved SQL word: {name}")


def safe_name_log(name: str, max_length: int = 50) -> str:
    """
    Create a safe version of a name for logging (truncate if too long).

    Args:
        name (str): Name to make safe for logging
        max_length (int): Maximum length for log output

    Returns:
        str: Safe name for logging
    """
    if not name:
        return "<empty>"

    if len(name) <= max_length:
        return name

    return f"{name[: max_length - 3]}..."


def validate_connection_string(
    connection_string: str, expected_analysis: Optional[str] = None
) -> None:
    """
    Validate a connection string format.

    Args:
        connection_string (str): Connection string to validate
        expected_analysis (Optional[str]): Expected URL analysis (e.g., "postgres")

    Raises:
        ValidationError: If connection string is invalid

    Returns:
        None
    """
    if not connection_string:
        raise ValidationError("Connection string cannot be empty")

    if expected_analysis and not connection_string.startswith(f"{expected_analysis}://"):
        raise ValidationError(
            f"Connection string must start with '{expected_analysis}://': {connection_string[:50]}..."
        )

    # Basic URL format validation
    if "://" in connection_string:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(connection_string)
            if not parsed.analysis or not parsed.netloc:
                raise ValidationError(
                    f"Invalid connection string format: {connection_string[:50]}..."
                )
        except Exception as e:
            raise ValidationError(f"Invalid connection string: {e}")
