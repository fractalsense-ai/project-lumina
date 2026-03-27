"""Shim: canonical source at domain-packs/system/controllers/yaml_converter.py"""
import sys
from lumina.systools._domain_pack_loader import load_domain_pack_module as _l
_canonical = _l("domain-packs/system/controllers/yaml_converter.py")
sys.modules[__name__] = _canonical