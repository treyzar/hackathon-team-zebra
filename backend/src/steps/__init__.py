"""Step types. Importing this package registers all built-in types."""

from steps.registry import build_payload_union
from steps.types import (  # noqa: F401
    choice,
    free_text,
    number,
    programming,
    short_text,
    theory,
)

# Discriminated union of every registered type's authored payload.
StepPayload = build_payload_union()
