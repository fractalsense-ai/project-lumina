"""Shim: canonical source at domain-packs/system/domain-lib/sensors/hw_temp.py"""
from lumina.systools._domain_pack_loader import load_domain_pack_module as _l
_mod = _l("domain-packs/system/domain-lib/sensors/hw_temp.py")
get_cpu_temp = _mod.get_cpu_temp