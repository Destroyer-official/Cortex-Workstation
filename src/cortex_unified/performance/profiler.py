"""
Performance profiling and monitoring for Cortex Cleaner operations.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager

@dataclass
class ProfileReport:
    """Profile Report.

 Handles profile report for.
 """
    operation_name: str
    total_time: float
    memory_usage: Dict[str, float] = field(default_factory=dict)
    cpu_usage: Dict[str, float] = field(default_factory=dict)
    io_stats: Dict[str, Any] = field(default_factory=dict)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """To dict.

 Handles to dict for.

 Returns:
 Dict[str, Any]: Dictionary mapping identifiers to status or values.
 """
        return {
            'operation_name': self.operation_name,
            'total_time': self.total_time,
            'memory_usage': self.memory_usage,
            'cpu_usage': self.cpu_usage,
            'io_stats': self.io_stats,
            'custom_metrics': self.custom_metrics
        }

class OperationProfiler:
    """Operation Profiler.

 Handles operation profiler for.
 """
    
    def __init__(self):
        """Initialize the instance and configure internal state.

        Sets up sub-widgets, event signal connections, and default options.
        """
        self.logger = logging.getLogger(__name__)
        self.profiles: List[ProfileReport] = []
        self.current_operation: Optional[str] = None
        self.start_time: Optional[float] = None
    
    @contextmanager
    def profile_operation(self, operation_name: str):
        """Context manager for profiling operations.

 Handles profile operation for.

 Args:
 operation_name (str): The operation name parameter.
 """
        self.start_operation(operation_name)
        try:
            yield self
        finally:
            self.end_operation()
    
    def start_operation(self, operation_name: str) -> None:
        """Start profiling an operation.

 Handles start operation for.

 Args:
 operation_name (str): The operation name parameter.
 """
        self.current_operation = operation_name
        self.start_time = time.time()
        self.logger.debug(f"Started profiling: {operation_name}")
    
    def end_operation(self) -> ProfileReport:
        """End profiling and create report.

 Handles end operation for.

 Returns:
 ProfileReport: Result of the operation.
 """
        if not self.current_operation or not self.start_time:
            raise ValueError("No operation currently being profiled")
        
        total_time = time.time() - self.start_time
        
        report = ProfileReport(
            operation_name=self.current_operation,
            total_time=total_time
        )
        
        self.profiles.append(report)
        self.logger.debug(f"Completed profiling: {self.current_operation} ({total_time:.3f}s)")
        
        self.current_operation = None
        self.start_time = None
        
        return report
    
    def get_reports(self) -> List[ProfileReport]:
        """Get all profiling reports.

 Handles get reports for.

 Returns:
 List[ProfileReport]: List of processed items or identifiers.
 """
        return self.profiles.copy()
    
    def get_report_by_name(self, operation_name: str) -> List[ProfileReport]:
        """Get reports for specific operation.

 Handles get report by name for.

 Args:
 operation_name (str): The operation name parameter.

 Returns:
 List[ProfileReport]: List of processed items or identifiers.
 """
        return [r for r in self.profiles if r.operation_name == operation_name]
    
    def clear_reports(self) -> None:
        """Clear all profiling reports.

 Handles clear reports for.
 """
        self.profiles.clear()
        self.logger.debug("Cleared all profiling reports")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all profiling data.

 Handles get summary for.

 Returns:
 Dict[str, Any]: Dictionary mapping identifiers to status or values.
 """
        if not self.profiles:
            return {}
        
        operations = {}
        for report in self.profiles:
            name = report.operation_name
            if name not in operations:
                operations[name] = {
                    'count': 0,
                    'total_time': 0.0,
                    'min_time': float('inf'),
                    'max_time': 0.0
                }
            
            ops = operations[name]
            ops['count'] += 1
            ops['total_time'] += report.total_time
            ops['min_time'] = min(ops['min_time'], report.total_time)
            ops['max_time'] = max(ops['max_time'], report.total_time)
        
        # Calculate averages
        for name, ops in operations.items():
            ops['avg_time'] = ops['total_time'] / ops['count']
        
        return operations