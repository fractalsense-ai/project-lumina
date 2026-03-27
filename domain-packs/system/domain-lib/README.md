# System Domain Library (`domain-lib/`)

Passive state estimators and shared libraries for the **system** domain pack.

## Components

| File | Purpose |
|------|---------|
| `system_health.py` | Aggregates hw probe results into `SystemHealthState` |
| `hw_probes/hw_disk.py` | Disk usage (stub  needs psutil) |
| `hw_probes/hw_memory.py` | Memory usage (stub  needs psutil) |
| `hw_probes/hw_temp.py` | CPU temperature (stub  platform-specific) |
| `hw_probes/hw_gpu.py` | GPU VRAM utilisation (stub  needs pynvml) |
| `hw_probes/hw_loop_latency.py` | Asyncio event-loop latency |
| `hw_probes/hw_http_queue.py` | In-flight HTTP request counter |

## Calling Convention

These are called by the **system runtime adapter** each orchestration
cycle.  They are **never** called directly by the core orchestrator.

Compatibility shims at `src/lumina/systools/` and `src/lumina/lib/`
re-export these APIs so existing imports continue to work.