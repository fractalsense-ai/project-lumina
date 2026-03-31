"""Backward-compatibility shim  real implementation moved to lumina.daemon.report."""
from lumina.daemon.report import *  # noqa: F401,F403
from lumina.daemon.report import Proposal, TaskResult, NightCycleReport
