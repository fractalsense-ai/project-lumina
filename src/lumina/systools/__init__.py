"""lumina.systools - Compatibility shims for system domain pack.

Canonical source: domain-packs/system/
Shim layer:       src/lumina/systools/

The real implementations have been relocated to the system domain pack
(domain-packs/system/controllers/ for active tools, domain-packs/system/
domain-lib/hw_probes/ for passive probes).  Each module in this package
is a thin shim that loads from the canonical location and re-exports
its public API so that existing ``from lumina.systools.X import Y``
statements continue to work without modification.

See also: ``lumina.systools._domain_pack_loader``
"""