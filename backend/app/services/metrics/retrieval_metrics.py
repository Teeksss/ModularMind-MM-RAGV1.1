from typing import Dict, Any, List, Optional, Callable
import logging
import time
import json
import threading
import asyncio
from datetime import datetime, timedelta
from functools import wraps

from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Optional: Import prometheus client if available
try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("Prometheus client not available. Metrics will be logged but not exposed via Prometheus.")
    PROMETHEUS_AVAILABLE = False


class RetrievalMetrics:
    """
    Metrics collection and monitoring for retrieval operations.
    
    Tracks and exposes metrics about retrieval performance:
    - Latency (overall and by stage)
    - Success/failure rates
    - Result counts
    - Cache hit rates
    - Query types and strategies
    """
    
    def __init__(self):
        """Initialize retrieval metrics collection."""
        self.metrics_enabled = settings.metrics.metrics_enabled
        
        # In-memory metrics storage
        self.retrieval_times = []  # list of retrieval latencies
        self.strategy_counts = {}  # counts by strategy
        self.query_type_counts = {}  # counts by query type
        self.error_counts = {}  # counts by error type
        self.result_counts = []  # list of result counts
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Interval metrics (last hour)
        self.interval_metrics = {
            "start_time": datetime.now(),
            "retrieval_count": 0,
            "total_latency": 0,
            "max_latency": 0,
            "error_count": 0
        }
        
        # Rolling window size
        self.max_samples = 1000
        
        # Lock for thread safety
        self.metrics_lock = threading.Lock()
        
        # Initialize Prometheus metrics if available
        if PROMETHEUS_AVAILABLE and self.metrics_enabled:
            self._init_prometheus_metrics()
        
        logger.info("Initialized RetrievalMetrics")
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        # Latency metrics
        self.retrieval_latency = Histogram(
            'retrieval_latency_seconds',
            'Retrieval operation latency in seconds',
            ['stage', 'method']
        )
        
        # Count metrics
        self.retrieval_count = Counter(
            'retrieval_total',
            'Total number of retrieval operations',
            ['method', 'status']
        )
        
        # Result metrics
        self.result_count = Histogram(
            'retrieval_result_count',
            'Number of results returned by retrieval operations',
            ['method']
        )
        
        # Cache metrics
        self.cache_ratio = Gauge(
            'retrieval_cache_hit_ratio',
            'Ratio of cache hits to total retrievals'
        )
        
        # Stage timing
        self.stage_timing = Histogram(
            'retrieval_stage_seconds',
            'Time spent in various retrieval stages',
            ['stage', 'method']
        )
    
    def track_retrieval(self, method=None):
        """
        Decorator to track retrieval metrics.
        
        Usage:
        @retrieval_metrics.track_retrieval(method="hybrid")
        async def my_retrieval_function(query, **kwargs):
            # Function implementation
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Skip metrics if disabled
                if not self.metrics_enabled:
                    return await func(*args, **kwargs)
                
                # Get retrieval method
                retrieval_method = method
                if not retrieval_method and "method" in kwargs:
                    retrieval_method = kwargs["method"]
                if not retrieval_method:
                    retrieval_method = "unknown"
                
                # Track start time
                start_time = time.time()
                error = None
                
                try:
                    # Track stage timings if the function supports it
                    if "track_stage" in kwargs:
                        stage_tracker = StageTracker(self, retrieval_method)
                        kwargs["track_stage"] = stage_tracker.track_stage
                    
                    # Execute the retrieval function
                    result = await func(*args, **kwargs)
                    
                    # Record successful retrieval
                    if PROMETHEUS_AVAILABLE:
                        self.retrieval_count.labels(method=retrieval_method, status="success").inc()
                    
                    return result
                    
                except Exception as e:
                    # Record error
                    error = str(e)
                    error_type = type(e).__name__
                    
                    if PROMETHEUS_AVAILABLE:
                        self.retrieval_count.labels(method=retrieval_method, status="error").inc()
                    
                    with self.metrics_lock:
                        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
                    
                    # Re-raise the exception
                    raise
                    
                finally:
                    # Calculate latency
                    latency = time.time() - start_time
                    
                    # Update metrics
                    self._update_metrics(retrieval_method, latency, error)
                    
                    # Record in Prometheus
                    if PROMETHEUS_AVAILABLE:
                        self.retrieval_latency.labels(
                            stage="total", method=retrieval_method
                        ).observe(latency)
            
            return wrapper
        
        return decorator
    
    def _update_metrics(self, method: str, latency: float, error: Optional[str] = None):
        """Update internal metrics."""
        with self.metrics_lock:
            # Add to retrieval times list (with rolling window)
            self.retrieval_times.append(latency)
            if len(self.retrieval_times) > self.max_samples:
                self.retrieval_times.pop(0)
            
            # Update strategy counts
            self.strategy_counts[method] = self.strategy_counts.get(method, 0) + 1
            
            # Update interval metrics
            self.interval_metrics["retrieval_count"] += 1
            self.interval_metrics["total_latency"] += latency
            self.interval_metrics["max_latency"] = max(self.interval_metrics["max_latency"], latency)
            
            if error:
                self.interval_metrics["error_count"] += 1
    
    def record_results(self, method: str, result_count: int):
        """Record number of results returned."""
        if not self.metrics_enabled:
            return
        
        with self.metrics_lock:
            # Add to result counts list (with rolling window)
            self.result_counts.append(result_count)
            if len(self.result_counts) > self.max_samples:
                self.result_counts.pop(0)
        
        # Record in Prometheus
        if PROMETHEUS_AVAILABLE:
            self.result_count.labels(method=method).observe(result_count)
    
    def record_cache_access(self, hit: bool):
        """Record cache hit or miss."""
        if not self.metrics_enabled:
            return
        
        with self.metrics_lock:
            if hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
        
        # Update Prometheus gauge
        if PROMETHEUS_AVAILABLE and (self.cache_hits + self.cache_misses) > 0:
            ratio = self.cache_hits / (self.cache_hits + self.cache_misses)
            self.cache_ratio.set(ratio)
    
    def record_query_type(self, query_type: str):
        """Record query type for analytics."""
        if not self.metrics_enabled:
            return
        
        with self.metrics_lock:
            self.query_type_counts[query_type] = self.query_type_counts.get(query_type, 0) + 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics as a dictionary."""
        with self.metrics_lock:
            # Calculate stats
            avg_latency = sum(self.retrieval_times) / len(self.retrieval_times) if self.retrieval_times else 0
            max_latency = max(self.retrieval_times) if self.retrieval_times else 0
            p95_latency = self._percentile(self.retrieval_times, 95)
            
            # Calculate cache hit rate
            total_cache_accesses = self.cache_hits + self.cache_misses
            cache_hit_rate = self.cache_hits / total_cache_accesses if total_cache_accesses > 0 else 0
            
            # Return compiled metrics
            return {
                "latency": {
                    "average": avg_latency,
                    "max": max_latency,
                    "p95": p95_latency,
                    "samples": len(self.retrieval_times)
                },
                "counts": {
                    "by_strategy": self.strategy_counts,
                    "by_query_type": self.query_type_counts,
                    "errors": self.error_counts
                },
                "results": {
                    "average": sum(self.result_counts) / len(self.result_counts) if self.result_counts else 0,
                    "total": sum(self.result_counts)
                },
                "cache": {
                    "hits": self.cache_hits,
                    "misses": self.cache_misses,
                    "hit_rate": cache_hit_rate
                },
                "interval": {
                    "start_time": self.interval_metrics["start_time"].isoformat(),
                    "retrievals": self.interval_metrics["retrieval_count"],
                    "avg_latency": (
                        self.interval_metrics["total_latency"] / self.interval_metrics["retrieval_count"]
                        if self.interval_metrics["retrieval_count"] > 0 else 0
                    ),
                    "max_latency": self.interval_metrics["max_latency"],
                    "error_rate": (
                        self.interval_metrics["error_count"] / self.interval_metrics["retrieval_count"]
                        if self.interval_metrics["retrieval_count"] > 0 else 0
                    )
                },
                "timestamp": datetime.now().isoformat()
            }
    
    def reset_interval_metrics(self):
        """Reset interval metrics for the next time period."""
        with self.metrics_lock:
            self.interval_metrics = {
                "start_time": datetime.now(),
                "retrieval_count": 0,
                "total_latency": 0,
                "max_latency": 0,
                "error_count": 0
            }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a list of values."""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * len(sorted_data)
        
        if index.is_integer():
            index = int(index)
            return sorted_data[index - 1] if index > 0 else sorted_data[0]
        else:
            index = int(index)
            return sorted_data[index]


class StageTracker:
    """Helper class for tracking timing of individual retrieval stages."""
    
    def __init__(self, metrics: RetrievalMetrics, method: str):
        """Initialize stage tracker."""
        self.metrics = metrics
        self.method = method
        self.stages = {}
        self.current_stage = None
        self.stage_start = None
    
    def track_stage(self, stage: str, start: bool = True):
        """
        Track timing for a retrieval stage.
        
        Args:
            stage: Name of the stage
            start: Whether this is the start (True) or end (False) of the stage
        """
        if not self.metrics.metrics_enabled:
            return
        
        current_time = time.time()
        
        if start:
            # End previous stage if exists
            if self.current_stage and self.stage_start:
                stage_time = current_time - self.stage_start
                self.stages[self.current_stage] = self.stages.get(self.current_stage, 0) + stage_time
                
                # Record in Prometheus
                if PROMETHEUS_AVAILABLE:
                    self.metrics.stage_timing.labels(
                        stage=self.current_stage, method=self.method
                    ).observe(stage_time)
            
            # Start new stage
            self.current_stage = stage
            self.stage_start = current_time
        else:
            # End current stage if it matches
            if self.current_stage == stage and self.stage_start:
                stage_time = current_time - self.stage_start
                self.stages[stage] = self.stages.get(stage, 0) + stage_time
                
                # Record in Prometheus
                if PROMETHEUS_AVAILABLE:
                    self.metrics.stage_timing.labels(
                        stage=stage, method=self.method
                    ).observe(stage_time)
                
                self.current_stage = None
                self.stage_start = None


# Create a singleton instance
_retrieval_metrics = RetrievalMetrics()

def get_retrieval_metrics() -> RetrievalMetrics:
    """Get the retrieval metrics singleton."""
    return _retrieval_metrics