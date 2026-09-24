"""Step types. Importing this package registers all built-in types."""

from steps.registry import build_payload_union
from steps.types import choice, free_text, programming, theory  # noqa: F401

# Discriminated union of every registered type's authored payload.
StepPayload = build_payload_union()
