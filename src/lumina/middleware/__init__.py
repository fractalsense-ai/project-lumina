"""Inspection middleware: the deterministic boundary between LLM output and execution.

This package implements Tier 2 (Inspection) of the Three-Tier Execution Pipeline:

    Ingestion (sensors / domain library)
        → **Inspection (middleware)**
            → Execution (actuators / tool adapters)

The middleware intercepts the LLM's generated output and verifies that it
strictly obeys the domain physics before allowing it to proceed.  Tool
adapters (actuators) must **never** fire unless the middleware gives the
green light.

Public API
----------
InspectionPipeline  — orchestrates the full validation chain
InspectionResult    — immutable result of a pipeline run
evaluate_check_expr — domain-pack invariant expression evaluator
parse_check_literal — literal parser for check expression RHS
validate_output     — schema-based output validation
validate_command    — Default Deny admin command validation
"""

from lumina.middleware.command_schema_registry import (
    validate_command,
)
from lumina.middleware.invariant_checker import (
    evaluate_check_expr,
    evaluate_invariants,
    parse_check_literal,
)
from lumina.middleware.output_validator import validate_output
from lumina.middleware.pipeline import InspectionPipeline, InspectionResult

__all__ = [
    "InspectionPipeline",
    "InspectionResult",
    "evaluate_check_expr",
    "evaluate_invariants",
    "parse_check_literal",
    "validate_command",
    "validate_output",
]
