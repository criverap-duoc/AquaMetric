"""AquaMetric API package."""

SERVICE_NAME = "aquametric-api"

# Kept in sync with pyproject.toml: the process cannot read installed metadata
# because the API is run from source, and /health must report a traceable version.
__version__ = "0.1.0"
