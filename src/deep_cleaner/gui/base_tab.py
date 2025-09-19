"""Base tab class for Deep Cleaner GUI tabs."""

from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QThread


class BaseTab(QWidget, ABC):
    """Base class for all GUI tabs."""
    
    def __init__(self, config, logger):
        super().__init__()
        self.config = config
        self.logger = logger
        self.worker_threads = []
        
        self.setup_ui()
        self.setup_connections()
        self.setup_tooltips()
    
    @abstractmethod
    def setup_ui(self):
        """Set up the user interface. Must be implemented by subclasses."""
        pass
    
    def setup_connections(self):
        """Set up signal connections. Can be overridden by subclasses."""
        pass
    
    def setup_tooltips(self):
        """Set up tooltips. Can be overridden by subclasses."""
        pass
    
    def cleanup(self):
        """Clean up resources when tab is closed."""
        # Stop all worker threads
        for thread in self.worker_threads:
            if thread and thread.isRunning():
                try:
                    thread.quit()
                    thread.wait(3000)  # Wait up to 3 seconds
                except RuntimeError:
                    pass  # Thread already deleted
        
        self.worker_threads.clear()
    
    def add_worker_thread(self, thread: QThread):
        """Add a worker thread to be managed."""
        self.worker_threads.append(thread)
    
    def remove_worker_thread(self, thread: QThread):
        """Remove a worker thread from management."""
        if thread in self.worker_threads:
            self.worker_threads.remove(thread)
    
    def format_bytes(self, bytes_value):
        """Format bytes to human readable format."""
        if bytes_value == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"