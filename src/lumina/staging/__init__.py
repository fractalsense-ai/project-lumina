"""File Generation & Staging — LLM-to-disk isolation layer.

The staging subsystem enforces the Brain → Checkpoint → Actuator
pipeline: LLM-generated payloads are **validated** by the Inspection
Pipeline, **staged** as JSON envelopes under ``data/staging/``, and only
written to their final destinations after explicit human approval.

Public API
----------
StagingService     — stage / list / approve / reject workflow
TemplateRegistry   — maps template_id → blank templates
write_from_template — deterministic actuator (atomic write)
"""

from lumina.staging.template_registry import TemplateRegistry
from lumina.staging.file_writer import write_from_template
from lumina.staging.staging_service import StagedFile, StagingService

__all__ = [
    "StagedFile",
    "StagingService",
    "TemplateRegistry",
    "write_from_template",
]
