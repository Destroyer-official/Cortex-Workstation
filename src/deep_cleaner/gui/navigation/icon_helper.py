"""Icon helper for navigation system."""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication, QStyle
from typing import Optional


class IconHelper:
    """Helper class for creating and managing navigation icons."""
    
    @staticmethod
    def create_text_icon(text: str, size: QSize = QSize(16, 16), color: str = "#495057") -> QIcon:
        """
        Create an icon from text (useful for simple text-based icons).
        
        Args:
            text: Text to display (usually 1-2 characters)
            size: Size of the icon
            color: Color of the text
            
        Returns:
            QIcon with the text rendered
        """
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font
        font = QFont()
        font.setBold(True)
        font.setPointSize(max(8, size.width() // 2))
        painter.setFont(font)
        
        # Set color
        painter.setPen(Qt.GlobalColor.black if color == "#495057" else Qt.GlobalColor.white)
        
        # Draw text centered
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
    
    @staticmethod
    def get_standard_icon(icon_type: QStyle.StandardPixmap) -> QIcon:
        """
        Get a standard Qt icon.
        
        Args:
            icon_type: Qt standard icon type
            
        Returns:
            QIcon from Qt's standard icons
        """
        app = QApplication.instance()
        if app:
            return app.style().standardIcon(icon_type)
        return QIcon()
    
    @staticmethod
    def get_navigation_icons() -> dict:
        """
        Get a dictionary of icons for common navigation items.
        
        Returns:
            Dictionary mapping tab names to QIcon objects
        """
        icons = {}
        
        # Use simple text-based icons for now (can be replaced with actual icons later)
        icon_mappings = {
            "Dashboard": "D",
            "Cleaner": "C",
            "Duplicates": "Du",
            "Temp Files": "T",
            "Large Files": "L",
            "Disk Analyzer": "DA",
            "System Tools": "ST",
            "Docker": "Do",
            "Package Managers": "P",
            "Heuristics": "H",
            "Broken Links": "BL",
            "Restore": "R",
            "Settings": "S",
            "File Shredder": "FS",
            "Scheduler": "Sc",
            "Reports": "Re",
            "Resource Monitor": "RM"
        }
        
        for name, emoji in icon_mappings.items():
            # For now, create simple text icons
            # In the future, these could be replaced with proper icon files
            icons[name] = IconHelper.create_text_icon(emoji[:2] if len(emoji) > 1 else emoji)
            
        return icons
    
    @staticmethod
    def create_colored_circle_icon(color: str, size: QSize = QSize(16, 16)) -> QIcon:
        """
        Create a simple colored circle icon.
        
        Args:
            color: Color of the circle (hex string)
            size: Size of the icon
            
        Returns:
            QIcon with a colored circle
        """
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle
        painter.setBrush(Qt.GlobalColor.blue if color == "#007bff" else Qt.GlobalColor.gray)
        painter.setPen(Qt.PenStyle.NoPen)
        
        margin = 2
        painter.drawEllipse(margin, margin, size.width() - 2*margin, size.height() - 2*margin)
        painter.end()
        
        return QIcon(pixmap)