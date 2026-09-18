"""Tool definitions for caching engine evaluation."""

from typing import Any, Dict


def doc_lookup(query: str) -> Dict[str, Any]:
    """Retrieve technical specifications, threading model, and memory overhead for Redis Cluster and KeyDB."""
    q = query.lower()
    docs = {
        "redis_cluster": {
            "engine": "Redis Cluster",
            "architecture": "Single-threaded event loop per node for command processing with asynchronous I/O threads",
            "clustering": "Fixed 16,384 hash slots distributed across primary and replica instances",
            "threading_model": "Single-threaded execution core per shard; requires running multiple node processes to utilize multi-core systems",
            "memory_overhead_per_key": "54-65 bytes baseline dict entry and robj metadata overhead per key",
            "throughput_100k_rps": "Requires 4-6 primary shards to comfortably handle 100k read req/sec with head-room",
            "low_memory_profile": "Higher baseline overhead in small-value workloads due to per-node jemalloc fragmentation and cluster bus metadata",
        },
        "keydb": {
            "engine": "KeyDB",
            "architecture": "Multithreaded drop-in alternative with shared-nothing architecture across worker threads",
            "clustering": "Supports active-replication and multi-threaded single-instance or clustered modes",
            "threading_model": "Multi-threaded event loop; can saturate all available CPU cores within a single instance",
            "memory_overhead_per_key": "42-50 bytes baseline overhead with optimized memory allocators and compact dict representation",
            "throughput_100k_rps": "Can achieve 100k read req/sec on a single 4-8 core instance without cluster sharding overhead",
            "low_memory_profile": "Lower overall memory overhead for multi-core deployments because it eliminates multi-process cluster bus and duplicate buffer overhead",
        },
    }

    if "redis" in q and "keydb" not in q:
        return {"result": docs["redis_cluster"]}
    if "keydb" in q and "redis" not in q:
        return {"result": docs["keydb"]}
    return {"result": docs}


def latency_math_engine(throughput_rps: int, cores: int) -> Dict[str, Any]:
    """Calculate per-core load, saturation risk, and projected p99 latency."""
    safe_cores = max(int(cores), 1)
    safe_rps = max(int(throughput_rps), 1)
    per_core_rps = safe_rps / safe_cores
    capacity_per_core = 25000.0
    utilization_ratio = min(per_core_rps / capacity_per_core, 0.98)
    core_utilization_pct = round(utilization_ratio * 100.0, 2)
    base_latency_ms = 0.35
    queue_delay_ms = (utilization_ratio / (1.0 - utilization_ratio)) * 0.12
    projected_p99_ms = round(base_latency_ms + queue_delay_ms, 3)

    return {
        "target_throughput_rps": safe_rps,
        "cores": safe_cores,
        "per_core_rps": round(per_core_rps, 1),
        "core_utilization_pct": core_utilization_pct,
        "projected_p99_latency_ms": projected_p99_ms,
        "status": "nominal" if core_utilization_pct < 80.0 else "saturated",
    }


def system_metrics_api(engine: str, mock_failure: bool = False) -> Dict[str, Any]:
    """Retrieve live telemetry and runtime metrics for a caching engine."""
    if mock_failure:
        return {
            "status": 504,
            "error": "Gateway Timeout: Telemetry daemon unreachable after 5000ms",
        }

    normalized = engine.strip().lower()
    if "keydb" in normalized:
        return {
            "status": 200,
            "engine": "KeyDB",
            "active_instances": 1,
            "threads_allocated": 8,
            "measured_qps": 104200,
            "avg_cpu_utilization_pct": 36.8,
            "memory_overhead_per_key_bytes": 46,
            "resident_memory_mb": 418.5,
            "p99_latency_ms": 0.46,
        }

    return {
        "status": 200,
        "engine": "Redis Cluster",
        "active_instances": 6,
        "shards": 3,
        "replicas": 3,
        "total_cores_allocated": 6,
        "measured_qps": 98900,
        "avg_cpu_utilization_pct": 69.1,
        "memory_overhead_per_key_bytes": 62,
        "resident_memory_mb": 534.2,
        "p99_latency_ms": 0.64,
    }
