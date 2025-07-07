"""
Metrics collection for KubeNetLLM framework.
"""

import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, Counter

import psutil
import structlog
from prometheus_client import Counter as PrometheusCounter, Histogram, Gauge

logger = structlog.get_logger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    """Resource usage snapshot"""
    cpu_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_bytes_sent: float
    network_bytes_recv: float
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """Collects and manages metrics for KubeNetLLM framework"""
    
    def __init__(self, enable_prometheus: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            enable_prometheus: Whether to enable Prometheus metrics
        """
        self.enable_prometheus = enable_prometheus
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        
        # Resource monitoring
        self.resource_history: List[ResourceUsage] = []
        self.monitoring_enabled = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Prometheus metrics
        if self.enable_prometheus:
            self._setup_prometheus_metrics()
        
        logger.info("Metrics collector initialized",
                   enable_prometheus=enable_prometheus)
    
    def _setup_prometheus_metrics(self) -> None:
        """Setup Prometheus metrics"""
        try:
            # Request metrics
            self.prom_request_counter = PrometheusCounter(
                'kubenet_requests_total',
                'Total number of requests',
                ['type', 'status']
            )
            
            self.prom_request_duration = Histogram(
                'kubenet_request_duration_seconds',
                'Request duration in seconds',
                ['type']
            )
            
            # LLM metrics
            self.prom_llm_api_calls = PrometheusCounter(
                'kubenet_llm_api_calls_total',
                'Total LLM API calls',
                ['provider', 'model']
            )
            
            self.prom_llm_tokens = Counter(
                'kubenet_llm_tokens_total',
                'Total tokens used',
                ['provider', 'type']
            )
            
            # Resource metrics
            self.prom_cpu_usage = Gauge(
                'kubenet_cpu_usage_percent',
                'CPU usage percentage'
            )
            
            self.prom_memory_usage = Gauge(
                'kubenet_memory_usage_mb',
                'Memory usage in MB'
            )
            
            # Validation metrics
            self.prom_validation_results = PrometheusCounter(
                'kubenet_validation_results_total',
                'Validation results',
                ['level', 'result']
            )
            
        except Exception as e:
            logger.warning("Failed to setup Prometheus metrics", error=str(e))
            self.enable_prometheus = False
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Increment value
            tags: Optional tags
        """
        self.counters[name] += value
        
        # Add to metrics history
        self.metrics[name].append(MetricPoint(
            name=name,
            value=self.counters[name],
            tags=tags or {}
        ))
        
        # Update Prometheus if enabled
        if self.enable_prometheus and hasattr(self, 'prom_request_counter'):
            if name == 'requests' and tags:
                self.prom_request_counter.labels(
                    type=tags.get('type', 'unknown'),
                    status=tags.get('status', 'unknown')
                ).inc(value)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric.
        
        Args:
            name: Gauge name
            value: Gauge value
            tags: Optional tags
        """
        self.gauges[name] = value
        
        # Add to metrics history
        self.metrics[name].append(MetricPoint(
            name=name,
            value=value,
            tags=tags or {}
        ))
        
        # Update Prometheus if enabled
        if self.enable_prometheus:
            if name == 'cpu_usage' and hasattr(self, 'prom_cpu_usage'):
                self.prom_cpu_usage.set(value)
            elif name == 'memory_usage' and hasattr(self, 'prom_memory_usage'):
                self.prom_memory_usage.set(value)
    
    def start_timer(self, name: str) -> None:
        """
        Start a timer.
        
        Args:
            name: Timer name
        """
        self.timers[name] = time.time()
    
    def stop_timer(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """
        Stop a timer and record duration.
        
        Args:
            name: Timer name
            tags: Optional tags
            
        Returns:
            Duration in seconds
        """
        if name not in self.timers:
            logger.warning("Timer not found", name=name)
            return 0.0
        
        duration = time.time() - self.timers[name]
        del self.timers[name]
        
        # Record duration
        self.metrics[f"{name}_duration"].append(MetricPoint(
            name=f"{name}_duration",
            value=duration,
            tags=tags or {}
        ))
        
        # Update Prometheus if enabled
        if self.enable_prometheus and hasattr(self, 'prom_request_duration'):
            self.prom_request_duration.labels(
                type=tags.get('type', 'unknown') if tags else 'unknown'
            ).observe(duration)
        
        return duration
    
    def record_llm_usage(self, provider: str, model: str, tokens: int, token_type: str = 'total') -> None:
        """
        Record LLM usage metrics.
        
        Args:
            provider: LLM provider name
            model: Model name
            tokens: Number of tokens
            token_type: Type of tokens (input/output/total)
        """
        self.increment_counter('llm_api_calls', tags={
            'provider': provider,
            'model': model
        })
        
        self.increment_counter('llm_tokens', value=tokens, tags={
            'provider': provider,
            'type': token_type
        })
        
        # Update Prometheus if enabled
        if self.enable_prometheus:
            if hasattr(self, 'prom_llm_api_calls'):
                self.prom_llm_api_calls.labels(
                    provider=provider,
                    model=model
                ).inc()
            
            if hasattr(self, 'prom_llm_tokens'):
                self.prom_llm_tokens.labels(
                    provider=provider,
                    type=token_type
                ).inc(tokens)
    
    def record_validation_result(self, level: str, result: str) -> None:
        """
        Record validation result.
        
        Args:
            level: Validation level
            result: Validation result (pass/fail)
        """
        self.increment_counter('validation_results', tags={
            'level': level,
            'result': result
        })
        
        # Update Prometheus if enabled
        if self.enable_prometheus and hasattr(self, 'prom_validation_results'):
            self.prom_validation_results.labels(
                level=level,
                result=result
            ).inc()
    
    def start_resource_monitoring(self, interval: float = 5.0) -> None:
        """
        Start resource monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.monitoring_enabled:
            return
        
        self.monitoring_enabled = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_resources,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        
        logger.info("Resource monitoring started", interval=interval)
    
    def stop_resource_monitoring(self) -> None:
        """Stop resource monitoring"""
        self.monitoring_enabled = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        logger.info("Resource monitoring stopped")
    
    def _monitor_resources(self, interval: float) -> None:
        """Monitor system resources"""
        process = psutil.Process()
        
        # Get initial I/O counters
        try:
            io_counters_start = process.io_counters()
            net_counters_start = psutil.net_io_counters()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            io_counters_start = None
            net_counters_start = None
        
        while self.monitoring_enabled:
            try:
                # CPU and memory
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / (1024 * 1024)
                
                # I/O counters
                disk_read_mb = 0
                disk_write_mb = 0
                net_sent = 0
                net_recv = 0
                
                try:
                    if io_counters_start:
                        io_counters = process.io_counters()
                        disk_read_mb = (io_counters.read_bytes - io_counters_start.read_bytes) / (1024 * 1024)
                        disk_write_mb = (io_counters.write_bytes - io_counters_start.write_bytes) / (1024 * 1024)
                    
                    if net_counters_start:
                        net_counters = psutil.net_io_counters()
                        net_sent = net_counters.bytes_sent - net_counters_start.bytes_sent
                        net_recv = net_counters.bytes_recv - net_counters_start.bytes_recv
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
                # Record resource usage
                usage = ResourceUsage(
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    disk_io_read_mb=disk_read_mb,
                    disk_io_write_mb=disk_write_mb,
                    network_bytes_sent=net_sent,
                    network_bytes_recv=net_recv
                )
                
                self.resource_history.append(usage)
                
                # Keep only last 1000 entries
                if len(self.resource_history) > 1000:
                    self.resource_history.pop(0)
                
                # Update gauges
                self.set_gauge('cpu_usage', cpu_percent)
                self.set_gauge('memory_usage', memory_mb)
                
                time.sleep(interval)
                
            except Exception as e:
                logger.warning("Resource monitoring error", error=str(e))
                time.sleep(interval)
    
    def get_counter(self, name: str) -> int:
        """Get counter value"""
        return self.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> float:
        """Get gauge value"""
        return self.gauges.get(name, 0.0)
    
    def get_resource_usage(self) -> Optional[ResourceUsage]:
        """Get latest resource usage"""
        if self.resource_history:
            return self.resource_history[-1]
        return None
    
    def get_average_resource_usage(self, minutes: int = 5) -> Optional[ResourceUsage]:
        """
        Get average resource usage over specified time period.
        
        Args:
            minutes: Number of minutes to average over
            
        Returns:
            Average resource usage or None if no data
        """
        if not self.resource_history:
            return None
        
        # Filter recent entries
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        recent_usage = [
            usage for usage in self.resource_history
            if usage.timestamp.timestamp() > cutoff_time
        ]
        
        if not recent_usage:
            return None
        
        # Calculate averages
        return ResourceUsage(
            cpu_percent=sum(u.cpu_percent for u in recent_usage) / len(recent_usage),
            memory_mb=sum(u.memory_mb for u in recent_usage) / len(recent_usage),
            disk_io_read_mb=sum(u.disk_io_read_mb for u in recent_usage) / len(recent_usage),
            disk_io_write_mb=sum(u.disk_io_write_mb for u in recent_usage) / len(recent_usage),
            network_bytes_sent=sum(u.network_bytes_sent for u in recent_usage) / len(recent_usage),
            network_bytes_recv=sum(u.network_bytes_recv for u in recent_usage) / len(recent_usage)
        )
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'resource_usage': self.get_resource_usage(),
            'average_resource_usage': self.get_average_resource_usage(),
            'total_data_points': sum(len(points) for points in self.metrics.values())
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics"""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.timers.clear()
        self.resource_history.clear()
        
        logger.info("Metrics reset")
    
    def export_metrics(self, format: str = 'json') -> str:
        """
        Export metrics in specified format.
        
        Args:
            format: Export format ('json' or 'prometheus')
            
        Returns:
            Exported metrics string
        """
        if format == 'json':
            import json
            return json.dumps(self.get_all_metrics(), indent=2, default=str)
        elif format == 'prometheus':
            # This would normally use prometheus_client.generate_latest()
            # For now, return a simple text format
            lines = []
            for name, value in self.counters.items():
                lines.append(f"kubenet_{name}_total {value}")
            for name, value in self.gauges.items():
                lines.append(f"kubenet_{name} {value}")
            return '\n'.join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def __del__(self):
        """Cleanup when collector is destroyed"""
        if self.monitoring_enabled:
            self.stop_resource_monitoring() 