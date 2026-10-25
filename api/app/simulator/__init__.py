"""Deterministic simulator: pure generation (02 §7) plus a thin HTTP CLI in `run.py`."""

from app.simulator.generator import generate_batch, generate_series
from app.simulator.scenario import Event, EventType, ScenarioConfig

__all__ = ["Event", "EventType", "ScenarioConfig", "generate_batch", "generate_series"]
