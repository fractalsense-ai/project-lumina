"""Backward-compatibility shim  real implementation moved to lumina.daemon.tasks."""
from lumina.daemon.tasks import *  # noqa: F401,F403
from lumina.daemon.tasks import (
    register_task,
    register_cross_domain_task,
    get_task,
    get_cross_domain_task,
    list_tasks,
    list_cross_domain_tasks,
)
# Re-export individual task functions that tests import by name
from lumina.daemon.tasks import (
    glossary_expansion,
    glossary_pruning,
    rejection_corpus_alignment,
    cross_module_consistency,
    knowledge_graph_rebuild,
    pacing_heuristic_recompute,
    domain_physics_constraint_refresh,
    slm_hint_generation,
    telemetry_summary_refresh,
    cross_domain_synthesis_task,
    logic_scrape_review,
    context_crawler,
    gated_staging,
    housekeeper_full_reindex,
    rebuild_domain_vectors,
)
