"""SQLAlchemy models; importing this package registers every table on `Base.metadata`.

Alembic's `env.py` imports `app.models` (not each module) so autogenerate always sees the
whole schema.
"""

from app.models.ingest_idempotency import IngestIdempotency
from app.models.observation import Observation
from app.models.sample import Sample
from app.models.site import Site
from app.models.spc_baseline import SpcBaseline

__all__ = ["IngestIdempotency", "Observation", "Sample", "Site", "SpcBaseline"]
