"""Performance optimization utilities for Deep Cleaner operations."""

import os
import gc
import threading
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import logging

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class OptimizationSettings:
    """Settings for performance optimization."""
    max_memory_mb: int = 0  # 0 = no limit
    max_cpu_percent: float = 80.0
    max_threads: int = 0  # 0 = auto-detect
    enable_gc_optimization: bool = True
    gc_threshold_multiplier: float = 2.0
    streaming_threshold_mb: int = 100
    checkpoint_interval: int = 1000
    io_buffer_size: int = 65536
    enable_compression: bool = True
    cache_size_mb: int = 50


class PerformanceOptimizer:
    """Optimizes performance for Deep Cleaner operations."""
    
    def __init__(self, settings: OptimizationSettings = None, logger: logging.Logger = None):
        """Initialize performance optimizer.
        
        Args:
            settings: Optimization settings
            logger: Logger instance
        """
        self.settings = settings or OptimizationSettings()
        self.logger = logger or logging.getLogger(__name__)
        self.original_gc_thresholds = None
        self.memory_monitor_active = False
        self.optimization_active = False
        
        # Performance tracking
        self.operation_stats = {}
        self.memory_usage_history = []
        self.gc_stats = {'collections': 0, 'time_spent': 0.0}
        
        if HAS_PSUTIL:
            self.process = psutil.Process()
        else:
            self.process = None
            self.logger.warning("psutil not available, some optimizations will be disabled")
    
    def start_optimization(self) -> None:
        """Start performance optimization."""
        if self.optimization_active:
            return
        
        self.optimization_active = True
        self.logger.info("Starting performance optimization")
        
        # Configure garbage collection
        if self.settings.enable_gc_optimization:
            self._optimize_garbage_collection()
        
        # Start memory monitoring
        self._start_memory_monitoring()
        
        # Set process priority if available
        if self.process:
            try:
                if hasattr(psutil, 'BELOW_NORMAL_PRIORITY_CLASS'):
                    self.process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                else:
                    self.process.nice(10)  # Lower priority on Unix
                self.logger.info("Set process to lower priority")
            except Exception as e:
                self.logger.warning(f"Could not set process priority: {e}")
    
    def stop_optimization(self) -> None:
        """Stop performance optimization and restore defaults."""
        if not self.optimization_active:
            return
        
        self.optimization_active = False
        self.logger.info("Stopping performance optimization")
        
        # Restore garbage collection settings
        if self.original_gc_thresholds:
            gc.set_threshold(*self.original_gc_thresholds)
        
        # Stop memory monitoring
        self.memory_monitor_active = False
        
        # Final garbage collection
        collected = gc.collect()
        if collected > 0:
            self.logger.info(f"Final garbage collection freed {collected} objects")
    
    def _optimize_garbage_collection(self) -> None:
        """Optimize garbage collection settings."""
        # Store original thresholds
        self.original_gc_thresholds = gc.get_threshold()
        
        # Set more aggressive thresholds for memory-intensive operations
        new_thresholds = tuple(
            int(threshold * self.settings.gc_threshold_multiplier)
            for threshold in self.original_gc_thresholds
        )
        
        gc.set_threshold(*new_thresholds)
        self.logger.info(f"Set GC thresholds from {self.original_gc_thresholds} to {new_thresholds}")
    
    def _start_memory_monitoring(self) -> None:
        """Start memory usage monitoring."""
        if not self.process:
            return
        
        self.memory_monitor_active = True
        
        def monitor_memory():
            while self.memory_monitor_active:
                try:
                    memory_info = self.process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                    
                    self.memory_usage_history.append(memory_mb)
                    
                    # Keep only recent history
                    if len(self.memory_usage_history) > 1000:
                        self.memory_usage_history = self.memory_usage_history[-500:]
                    
                    # Check memory limit
                    if (self.settings.max_memory_mb > 0 and 
                        memory_mb > self.settings.max_memory_mb):
                        self.logger.warning(f"Memory usage ({memory_mb:.1f} MB) exceeds limit ({self.settings.max_memory_mb} MB)")
                        self._trigger_memory_cleanup()
                    
                    time.sleep(5)  # Check every 5 seconds
                
                except Exception as e:
                    self.logger.error(f"Error monitoring memory: {e}")
                    break
        
        monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
        monitor_thread.start()
    
    def _trigger_memory_cleanup(self) -> None:
        """Trigger aggressive memory cleanup."""
        self.logger.info("Triggering memory cleanup")
        
        # Force garbage collection
        start_time = time.time()
        collected = gc.collect()
        gc_time = time.time() - start_time
        
        self.gc_stats['collections'] += 1
        self.gc_stats['time_spent'] += gc_time
        
        if collected > 0:
            self.logger.info(f"Garbage collection freed {collected} objects in {gc_time:.3f}s")
        
        # Clear internal caches if they exist
        self._clear_internal_caches()
    
    def _clear_internal_caches(self) -> None:
        """Clear internal caches to free memory."""
        # This would clear any internal caches maintained by Deep Cleaner
        # For now, just log the action
        self.logger.debug("Clearing internal caches")
    
    def get_optimal_thread_count(self, operation_type: str = "default") -> int:
        """Get optimal thread count for an operation.
        
        Args:
            operation_type: Type of operation (io_bound, cpu_bound, mixed)
        
        Returns:
            Optimal number of threads
        """
        if self.settings.max_threads > 0:
            max_threads = self.settings.max_threads
        else:
            cpu_count = os.cpu_count() or 2
            
            if operation_type == "io_bound":
                max_threads = cpu_count * 2
            elif operation_type == "cpu_bound":
                max_threads = cpu_count
            else:  # mixed or default
                max_threads = max(1, cpu_count // 2)
        
        # Adjust based on current system load
        if self.process:
            try:
                cpu_percent = self.process.cpu_percent()
                if cpu_percent > self.settings.max_cpu_percent:
                    max_threads = max(1, max_threads // 2)
            except Exception:
                pass
        
        return max_threads
    
    def get_optimal_buffer_size(self, file_size: int = 0) -> int:
        """Get optimal buffer size for file operations.
        
        Args:
            file_size: Size of file being processed
        
        Returns:
            Optimal buffer size in bytes
        """
        base_size = self.settings.io_buffer_size
        
        # Adjust based on file size
        if file_size > 100 * 1024 * 1024:  # > 100MB
            return min(base_size * 4, 1024 * 1024)  # Up to 1MB buffer
        elif file_size > 10 * 1024 * 1024:  # > 10MB
            return base_size * 2
        else:
            return base_size
    
    def should_use_streaming(self, data_size: int) -> bool:
        """Determine if streaming should be used for large data.
        
        Args:
            data_size: Size of data in bytes
        
        Returns:
            True if streaming should be used
        """
        size_mb = data_size / (1024 * 1024)
        return size_mb > self.settings.streaming_threshold_mb
    
    def optimize_for_operation(self, operation_name: str, 
                             operation_func: Callable, *args, **kwargs) -> Any:
        """Execute an operation with optimization.
        
        Args:
            operation_name: Name of the operation for tracking
            operation_func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Result of the operation
        """
        start_time = time.time()
        start_memory = self._get_current_memory_mb()
        
        try:
            # Pre-operation optimization
            if operation_name not in self.operation_stats:
                self.operation_stats[operation_name] = {
                    'count': 0,
                    'total_time': 0.0,
                    'avg_time': 0.0,
                    'max_memory': 0.0
                }
            
            # Execute operation
            result = operation_func(*args, **kwargs)
            
            # Post-operation tracking
            end_time = time.time()
            end_memory = self._get_current_memory_mb()
            
            operation_time = end_time - start_time
            memory_used = max(0, end_memory - start_memory)
            
            # Update statistics
            stats = self.operation_stats[operation_name]
            stats['count'] += 1
            stats['total_time'] += operation_time
            stats['avg_time'] = stats['total_time'] / stats['count']
            stats['max_memory'] = max(stats['max_memory'], memory_used)
            
            self.logger.debug(f"Operation {operation_name} completed in {operation_time:.3f}s, "
                            f"memory delta: {memory_used:.1f}MB")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error in optimized operation {operation_name}: {e}")
            raise
    
    def _get_current_memory_mb(self) -> float:
        """Get current memory usage in MB.
        
        Returns:
            Current memory usage in MB
        """
        if self.process:
            try:
                return self.process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass
        return 0.0
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report.
        
        Returns:
            Performance report dictionary
        """
        current_memory = self._get_current_memory_mb()
        
        report = {
            'optimization_active': self.optimization_active,
            'current_memory_mb': current_memory,
            'settings': {
                'max_memory_mb': self.settings.max_memory_mb,
                'max_cpu_percent': self.settings.max_cpu_percent,
                'max_threads': self.settings.max_threads,
                'streaming_threshold_mb': self.settings.streaming_threshold_mb
            },
            'gc_stats': self.gc_stats.copy(),
            'operation_stats': self.operation_stats.copy()
        }
        
        # Add memory usage statistics
        if self.memory_usage_history:
            report['memory_stats'] = {
                'min_mb': min(self.memory_usage_history),
                'max_mb': max(self.memory_usage_history),
                'avg_mb': sum(self.memory_usage_history) / len(self.memory_usage_history),
                'samples': len(self.memory_usage_history)
            }
        
        # Add system information if available
        if self.process:
            try:
                report['system_info'] = {
                    'cpu_count': os.cpu_count(),
                    'current_cpu_percent': self.process.cpu_percent(),
                    'available_memory_mb': psutil.virtual_memory().available / (1024 * 1024)
                }
            except Exception:
                pass
        
        return report
    
    def suggest_optimizations(self) -> list[str]:
        """Suggest performance optimizations based on current state.
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Analyze memory usage
        if self.memory_usage_history:
            max_memory = max(self.memory_usage_history)
            avg_memory = sum(self.memory_usage_history) / len(self.memory_usage_history)
            
            if max_memory > 1000:  # > 1GB
                suggestions.append("Consider setting a memory limit to prevent excessive usage")
            
            if avg_memory > 500:  # > 500MB average
                suggestions.append("Enable streaming mode for large datasets")
        
        # Analyze operation performance
        for op_name, stats in self.operation_stats.items():
            if stats['avg_time'] > 10.0:  # > 10 seconds average
                suggestions.append(f"Operation '{op_name}' is slow, consider optimization")
            
            if stats['max_memory'] > 200:  # > 200MB
                suggestions.append(f"Operation '{op_name}' uses significant memory, consider streaming")
        
        # Analyze garbage collection
        if self.gc_stats['collections'] > 0:
            avg_gc_time = self.gc_stats['time_spent'] / self.gc_stats['collections']
            if avg_gc_time > 0.1:  # > 100ms average
                suggestions.append("Frequent garbage collection detected, consider memory optimization")
        
        # System-specific suggestions
        if self.process:
            try:
                available_memory = psutil.virtual_memory().available / (1024 * 1024)
                if available_memory < 500:  # < 500MB available
                    suggestions.append("Low system memory, consider reducing memory limits")
                
                cpu_percent = self.process.cpu_percent()
                if cpu_percent > 80:
                    suggestions.append("High CPU usage, consider reducing thread count")
            except Exception:
                pass
        
        return suggestions
    
    def export_performance_data(self, filepath: str) -> bool:
        """Export performance data to file.
        
        Args:
            filepath: Path to export file
        
        Returns:
            True if export successful
        """
        try:
            import json
            from datetime import datetime
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'performance_report': self.get_performance_report(),
                'optimization_suggestions': self.suggest_optimizations(),
                'memory_history': self.memory_usage_history[-100:],  # Last 100 samples
            }
            
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Exported performance data to {filepath}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error exporting performance data: {e}")
            return False