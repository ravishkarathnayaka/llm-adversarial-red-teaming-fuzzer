"""Fuzzer extraction prober bridge."""

from benchmark_engine.strategies.boundary_tester import (
    BoundaryTester as ExtractionProber,
    BoundaryProbeResult,
)

__all__ = ["ExtractionProber", "BoundaryProbeResult"]
