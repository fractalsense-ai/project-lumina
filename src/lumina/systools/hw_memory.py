"""Shim: canonical source at domain-packs/system/domain-lib/hw_probes/hw_memory.py"""
from lumina.systools._domain_pack_loader import load_domain_pack_module as _l
_mod = _l("domain-packs/system/domain-lib/hw_probes/hw_memory.py")
get_memory_usage = _mod.get_memory_usage