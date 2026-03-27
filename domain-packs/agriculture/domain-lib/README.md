# Agriculture Domain Library

Shared pure-function libraries for the agriculture domain pack.
These are **Group Libraries** — loaded once by the runtime and cached
across all modules that reference them via `group_libraries` pointers
in their domain-physics files.

## Contents

| File                       | Description                                              |
|----------------------------|----------------------------------------------------------|
| `environmental_sensors.py` | Sensor normalization, tolerance checking, batch aggregation |
