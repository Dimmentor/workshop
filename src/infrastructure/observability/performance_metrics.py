import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager, contextmanager

from src.infrastructure.observability.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, success: bool = True, error_message: Optional[str] = None):
        """Mark operation as finished."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/tracing."""
        return {
            "operation_name": self.operation_name,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            **self.metadata
        }


class PerformanceTracker:
    """Tracks performance metrics across operations."""
    
    def __init__(self, max_history: int = 1000):
        self._metrics: List[PerformanceMetrics] = []
        self._max_history = max_history
    
    def add_metric(self, metric: PerformanceMetrics):
        """Add a performance metric."""
        self._metrics.append(metric)
        # Keep only recent metrics
        if len(self._metrics) > self._max_history:
            self._metrics = self._metrics[-self._max_history:]
    
    def get_metrics(self, operation_name: Optional[str] = None) -> List[PerformanceMetrics]:
        """Get metrics, optionally filtered by operation name."""
        if operation_name:
            return [m for m in self._metrics if m.operation_name == operation_name]
        return self._metrics.copy()
    
    def get_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        metrics = self.get_metrics(operation_name)
        if not metrics:
            return {}
        
        durations = [m.duration_ms for m in metrics if m.duration_ms is not None]
        successes = [m for m in metrics if m.success]
        
        return {
            "total_operations": len(metrics),
            "successful_operations": len(successes),
            "success_rate": len(successes) / len(metrics) * 100,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "operation_name": operation_name or "all"
        }
    
    def clear(self):
        """Clear all metrics."""
        self._metrics.clear()


# Global performance tracker
_performance_tracker = PerformanceTracker()


def get_performance_tracker() -> PerformanceTracker:
    """Get global performance tracker."""
    return _performance_tracker


@contextmanager
def track_performance(operation_name: str, **metadata: Any):
    """Context manager for tracking performance with Phoenix tracing."""
    start_time = time.time()
    metric = PerformanceMetrics(
        operation_name=operation_name,
        start_time=start_time,
        metadata=metadata
    )
    
    with tracer.start_as_current_span(f"perf.{operation_name}") as span:
        span.set_attribute("operation.name", operation_name)
        for key, value in metadata.items():
            span.set_attribute(f"operation.{key}", str(value))
        
        try:
            yield metric
            metric.finish(success=True)
            span.set_attribute("operation.success", True)
            span.set_attribute("operation.duration_ms", metric.duration_ms)
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            error_msg = str(e)
            metric.finish(success=False, error_message=error_msg)
            span.set_attribute("operation.success", False)
            span.set_attribute("operation.error", error_msg)
            span.set_attribute("operation.duration_ms", metric.duration_ms)
            raise
        finally:
            _performance_tracker.add_metric(metric)


@asynccontextmanager
async def track_performance_async(operation_name: str, **metadata: Any):
    """Async context manager for tracking performance with Phoenix tracing."""
    start_time = time.time()
    metric = PerformanceMetrics(
        operation_name=operation_name,
        start_time=start_time,
        metadata=metadata
    )
    
    with tracer.start_as_current_span(f"perf.{operation_name}") as span:
        span.set_attribute("operation.name", operation_name)
        for key, value in metadata.items():
            span.set_attribute(f"operation.{key}", str(value))
        
        try:
            yield metric
            metric.finish(success=True)
            span.set_attribute("operation.success", True)
            span.set_attribute("operation.duration_ms", metric.duration_ms)
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            error_msg = str(e)
            metric.finish(success=False, error_message=error_msg)
            span.set_attribute("operation.success", False)
            span.set_attribute("operation.error", error_msg)
            span.set_attribute("operation.duration_ms", metric.duration_ms)
            raise
        finally:
            _performance_tracker.add_metric(metric)


def track_function_performance(operation_name: str):
    """Decorator for tracking function performance."""
    def decorator(func):
        if hasattr(func, '__call__'):
            # Async function
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    async with track_performance_async(operation_name) as metric:
                        result = await func(*args, **kwargs)
                        metric.metadata.update({
                            "function": func.__name__,
                            "args_count": len(args),
                            "kwargs_count": len(kwargs)
                        })
                        return result
                return async_wrapper
            # Sync function
            else:
                def sync_wrapper(*args, **kwargs):
                    with track_performance(operation_name) as metric:
                        result = func(*args, **kwargs)
                        metric.metadata.update({
                            "function": func.__name__,
                            "args_count": len(args),
                            "kwargs_count": len(kwargs)
                        })
                        return result
                return sync_wrapper
        return func
    return decorator


# Specific performance tracking functions
def track_mcp_operation(server_name: str, tool_name: str):
    """Track MCP operation performance."""
    return track_performance(
        "mcp_operation",
        server_name=server_name,
        tool_name=tool_name
    )


def track_workflow_operation(node_name: str, workflow_type: str = "default"):
    """Track workflow operation performance."""
    return track_performance(
        "workflow_operation",
        node_name=node_name,
        workflow_type=workflow_type
    )


def track_cache_operation(cache_name: str, operation: str):
    """Track cache operation performance."""
    return track_performance(
        "cache_operation",
        cache_name=cache_name,
        operation=operation
    )


def track_llm_operation(model_name: str, operation: str):
    """Track LLM operation performance."""
    return track_performance(
        "llm_operation",
        model_name=model_name,
        operation=operation
    )