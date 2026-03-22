"""
lumina.system_log — System Log Micro-Router subsystem.

Public surface:
    event_payload   LogLevel, LogEvent, create_event
    log_bus         emit, emit_async, subscribe, start, stop
    log_router      start, stop  (registers routing rules on the bus)
    alert_store     warning_store, alert_store  (bounded in-memory stores)
"""

