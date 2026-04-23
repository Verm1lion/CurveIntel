"""
CurveIntel enum definitions.

Standardized enum values for material families, yield behavior,
anomaly categories, and data representations.
"""

from enum import Enum


class MaterialType(str, Enum):
    """Material family classification."""

    STEEL_STRUCTURAL = "structural_steel"  # S355, S690, and similar grades
    STEEL_DP = "dual_phase_steel"  # DP980, DP1180
    STEEL_LOW_CARBON = "low_carbon_steel"  # Q235, AISI 1018
    STEEL_STAINLESS = "stainless_steel"  # 316L, 304
    ALUMINUM = "aluminum"  # AA6xxx, 7075
    POLYMER = "polymer"  # FKM, PLA, PDMS
    COMPOSITE = "composite"  # CFRP
    UNKNOWN = "unknown"


class YieldBehavior(str, Enum):
    """Yield behavior classification."""

    CONTINUOUS = "continuous"  # Smooth yielding, use 0.2% offset
    DISCONTINUOUS = "discontinuous"  # Upper/lower yield with Luders plateau
    UNDEFINED = "undefined"  # Not classified yet


class AnomalyType(str, Enum):
    """Anomaly categories detected by the pipeline."""

    GRIP_SLIPPAGE = "grip_slippage"  # Grip slip
    SPIKE = "spike"  # Electrical spike
    PREMATURE_FRACTURE = "premature_fracture"  # Early fracture
    TOE_REGION = "toe_region"  # Seating artifact near the origin
    TRUNCATION = "truncation"  # Incomplete curve
    SENSOR_SATURATION = "sensor_saturation"  # Saturated load signal
    HIGH_NOISE = "high_noise"  # Excessive noise
    DOUBLE_YIELD = "double_yield"  # Informational upper/lower yield event
    NON_MONOTONIC = "non_monotonic"  # Cyclic or non-monotonic loading


class StepStatus(str, Enum):
    """Execution outcome for a pipeline step."""

    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


class StressStrainType(str, Enum):
    """Stress-strain representation type."""

    ENGINEERING = "engineering"  # Nominal engineering values
    TRUE = "true"  # True stress / true strain values
    RAW = "raw"  # Raw force-displacement measurements
