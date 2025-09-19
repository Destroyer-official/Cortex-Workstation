"""Resource monitoring and management for Deep Cleaner operations."""

import time
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import logging

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class SystemMetrics:
    """System resource metrics at a point in time."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    process_count: int
    thread_count: int


class ResourceMonitor:
    """Monitors system resources and provides optimization recommendations."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize resource monitor.
        
        Args:
            logger: Logger instance for monitoring events
        """
        self.logger = logger or logging.getLogger(__name__)
        self.monitoring = False
        self.monitor_thread = None
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1000
        self.monitor_interval = 1.0  # seconds
        self.callbacks: List[Callable[[SystemMetrics], None]] = []
        
        # Resource thresholds for warnings
        self.cpu_warning_threshold = 80.0
        self.memory_warning_threshold = 85.0
        self.disk_io_warning_threshold = 100.0  # MB/s
        
        if not HAS_PSUTIL:
            self.logger.warning("psutil not available, resource monitoring will be limited")
    
    def start_monitoring(self, interval: float = 1.0) -> None:
        """Start continuous resource monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.monitoring:
            return
        
        self.monitor_interval = interval
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"Started resource monitoring with {interval}s interval")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Stopped resource monitoring")
    
    def add_callback(self, callback: Callable[[SystemMetrics], None]) -> None:
        """Add callback for resource updates.
        
        Args:
            callback: Function to call with each metrics update
        """
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[SystemMetrics], None]) -> None:
        """Remove callback for resource updates.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get current system metrics.
        
        Returns:
            Current system metrics or None if unavailable
        """
        if not HAS_PSUTIL:
            return None
        
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Get disk I/O
            disk_io = psutil.disk_io_counters()
            disk_io_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
            disk_io_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0
            
            # Get network I/O
            network_io = psutil.net_io_counters()
            network_io_sent_mb = network_io.bytes_sent / (1024 * 1024) if network_io else 0
            network_io_recv_mb = network_io.bytes_recv / (1024 * 1024) if network_io else 0
            
            # Get process information
            process_count = len(psutil.pids())
            
            # Get current process thread count
            current_process = psutil.Process()
            thread_count = current_process.num_threads()
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_io_read_mb=disk_io_read_mb,
                disk_io_write_mb=disk_io_write_mb,
                network_io_sent_mb=network_io_sent_mb,
                network_io_recv_mb=network_io_recv_mb,
                process_count=process_count,
                thread_count=thread_count
            )
        
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return None
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        last_disk_io = None
        last_network_io = None
        
        while self.monitoring:
            try:
                metrics = self.get_current_metrics()
                if metrics:
                    # Calculate I/O rates if we have previous data
                    if last_disk_io and last_network_io:
                        time_diff = (metrics.timestamp - last_disk_io[0]).total_seconds()
                        if time_diff > 0:
                            disk_read_rate = (metrics.disk_io_read_mb - last_disk_io[1]) / time_diff
                            disk_write_rate = (metrics.disk_io_write_mb - last_disk_io[2]) / time_diff
                            net_sent_rate = (metrics.network_io_sent_mb - last_network_io[1]) / time_diff
                            net_recv_rate = (metrics.network_io_recv_mb - last_network_io[2]) / time_diff
                            
                            # Update metrics with rates
                            metrics.disk_io_read_mb = disk_read_rate
                            metrics.disk_io_write_mb = disk_write_rate
                            metrics.network_io_sent_mb = net_sent_rate
                            metrics.network_io_recv_mb = net_recv_rate
                    
                    # Store for rate calculation
                    last_disk_io = (metrics.timestamp, metrics.disk_io_read_mb, metrics.disk_io_write_mb)
                    last_network_io = (metrics.timestamp, metrics.network_io_sent_mb, metrics.network_io_recv_mb)
                    
                    # Add to history
                    self._add_to_history(metrics)
                    
                    # Check thresholds and warn if needed
                    self._check_thresholds(metrics)
                    
                    # Call callbacks
                    for callback in self.callbacks:
                        try:
                            callback(metrics)
                        except Exception as e:
                            self.logger.error(f"Error in resource monitor callback: {e}")
                
                time.sleep(self.monitor_interval)
            
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitor_interval)
    
    def _add_to_history(self, metrics: SystemMetrics) -> None:
        """Add metrics to history with size limit."""
        self.metrics_history.append(metrics)
        
        # Trim history if too large
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def _check_thresholds(self, metrics: SystemMetrics) -> None:
        """Check resource thresholds and log warnings."""
        if metrics.cpu_percent > self.cpu_warning_threshold:
            self.logger.warning(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.memory_warning_threshold:
            self.logger.warning(f"High memory usage: {metrics.memory_percent:.1f}%")
        
        total_disk_io = metrics.disk_io_read_mb + metrics.disk_io_write_mb
        if total_disk_io > self.disk_io_warning_threshold:
            self.logger.warning(f"High disk I/O: {total_disk_io:.1f} MB/s")
    
    def get_metrics_summary(self, duration_minutes: int = 5) -> Dict:
        """Get summary of metrics over specified duration.
        
        Args:
            duration_minutes: Duration to analyze in minutes
        
        Returns:
            Summary statistics dictionary
        """
        if not self.metrics_history:
            return {}
        
        # Filter metrics by duration
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        # Calculate statistics
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            'duration_minutes': duration_minutes,
            'sample_count': len(recent_metrics),
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'min': min(cpu_values),
                'max': max(cpu_values)
            },
            'memory': {
                'avg': sum(memory_values) / len(memory_values),
                'min': min(memory_values),
                'max': max(memory_values)
            },
            'memory_available_mb': recent_metrics[-1].memory_available_mb,
            'thread_count': recent_metrics[-1].thread_count
        }
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on current metrics.
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        if not self.metrics_history:
            return recommendations
        
        recent_summary = self.get_metrics_summary(2)  # Last 2 minutes
        if not recent_summary:
            return recommendations
        
        # CPU recommendations
        if recent_summary['cpu']['avg'] > 80:
            recommendations.append("Consider reducing CPU priority or thread count")
        elif recent_summary['cpu']['avg'] < 20:
            recommendations.append("CPU usage is low, consider increasing thread count")
        
        # Memory recommendations
        if recent_summary['memory']['avg'] > 85:
            recommendations.append("High memory usage detected, consider setting memory limits")
        elif recent_summary['memory_available_mb'] < 500:
            recommendations.append("Low available memory, consider enabling streaming mode")
        
        # Thread recommendations
        if recent_summary['thread_count'] > psutil.cpu_count() * 2:
            recommendations.append("High thread count may cause context switching overhead")
        
        return recommendations
    
    def should_throttle_operations(self) -> bool:
        """Determine if operations should be throttled based on system load.
        
        Returns:
            True if operations should be throttled
        """
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return False
        
        # Throttle if any resource is heavily loaded
        return (
            current_metrics.cpu_percent > self.cpu_warning_threshold or
            current_metrics.memory_percent > self.memory_warning_threshold or
            current_metrics.memory_available_mb < 200
        )
    
    def get_recommended_thread_count(self) -> int:
        """Get recommended thread count based on system load.
        
        Returns:
            Recommended number of threads
        """
        if not HAS_PSUTIL:
            return 2  # Conservative default
        
        cpu_count = psutil.cpu_count()
        current_metrics = self.get_current_metrics()
        
        if not current_metrics:
            return max(1, cpu_count // 2)
        
        # Adjust based on current load
        if current_metrics.cpu_percent > 80:
            return max(1, cpu_count // 4)  # Reduce threads under high load
        elif current_metrics.cpu_percent < 30:
            return cpu_count  # Use all cores under light load
        else:
            return max(1, cpu_count // 2)  # Balanced approach
    
    def export_metrics(self, filepath: str, duration_hours: int = 1) -> bool:
        """Export metrics history to file.
        
        Args:
            filepath: Path to export file
            duration_hours: Hours of history to export
        
        Returns:
            True if export successful
        """
        try:
            import json
            from pathlib import Path
            
            # Filter metrics by duration
            cutoff_time = datetime.now() - timedelta(hours=duration_hours)
            export_metrics = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'cpu_percent': m.cpu_percent,
                    'memory_percent': m.memory_percent,
                    'memory_available_mb': m.memory_available_mb,
                    'disk_io_read_mb': m.disk_io_read_mb,
                    'disk_io_write_mb': m.disk_io_write_mb,
                    'network_io_sent_mb': m.network_io_sent_mb,
                    'network_io_recv_mb': m.network_io_recv_mb,
                    'process_count': m.process_count,
                    'thread_count': m.thread_count
                }
                for m in self.metrics_history
                if m.timestamp >= cutoff_time
            ]
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'duration_hours': duration_hours,
                'metrics_count': len(export_metrics),
                'metrics': export_metrics,
                'summary': self.get_metrics_summary(duration_hours * 60)
            }
            
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Exported {len(export_metrics)} metrics to {filepath}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error exporting metrics: {e}")
            return False