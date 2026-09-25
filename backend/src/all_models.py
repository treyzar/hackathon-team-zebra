"""Imports every model module so BaseDB.metadata is complete (alembic, tests)."""

import courses.models  # noqa: F401
import files.models  # noqa: F401
import groups.models  # noqa: F401
import notifications.models  # noqa: F401
import submissions.models  # noqa: F401
from models import BaseDB

metadata = BaseDB.metadata
