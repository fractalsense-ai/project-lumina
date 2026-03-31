"""Backward-compatibility shim  real implementation moved to lumina.daemon.cross_domain."""
from lumina.daemon.cross_domain import *  # noqa: F401,F403
from lumina.daemon.cross_domain import (
    get_opt_in_config,
    is_mutual_peer,
    filter_mutual_pairs,
    compare_glossaries,
    compare_invariant_structures,
    find_synthesis_candidates,
)
