"""Enhanced reports and logs for Deep Cleaner."""

import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import html

from ..utils import normalize_path
from ..config import Config


class ReportsGenerator:
    """Generator for enhanced reports and logs."""
    
    def __init__(self, config: Config = None, reports_dir: str = None):
        """Initialize reports generator."""
        self.config = config or Config()
        self.reports_dir = reports_dir or self._get_default_reports_dir()
        self.error_count = 0
        
        # Create reports directory if it doesn't exist
        Path(self.reports_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_default_reports_dir(self) -> str:
        """Get the default reports directory."""
        home = Path.home()
        reports_dir = home / ".deepcleaner" / "reports"
        return str(reports_dir)
    
    def generate_text_report(self, data: Dict, report_name: str = None) -> str:
        """Generate a text report.
        
        Args:
            data: Data to include in the report
            report_name: Name for the report (optional)
            
        Returns:
            Path to the generated report file
        """
        try:
            # Generate report name if not provided
            if not report_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_name = f"report_{timestamp}.txt"
            
            # Create report content
            content = self._format_text_report(data)
            
            # Save report
            report_file = Path(self.reports_dir) / report_name
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return str(report_file)
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to generate text report: {str(e)}")
    
    def _format_text_report(self, data: Dict) -> str:
        """Format data as a text report."""
        lines = []
        lines.append("=" * 60)
        lines.append("DEEP CLEANER REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Add data sections
        self._add_text_section(lines, data, 0)
        
        lines.append("")
        lines.append("=" * 60)
        lines.append("END OF REPORT")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _add_text_section(self, lines: List[str], data: Dict, indent: int):
        """Add a section to the text report."""
        indent_str = "  " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent_str}{key}:")
                self._add_text_section(lines, value, indent + 1)
            elif isinstance(value, list):
                lines.append(f"{indent_str}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        self._add_text_section(lines, item, indent + 1)
                    else:
                        lines.append(f"{indent_str}  - {item}")
            else:
                lines.append(f"{indent_str}{key}: {value}")
    
    def generate_html_report(self, data: Dict, report_name: str = None) -> str:
        """Generate an HTML report.
        
        Args:
            data: Data to include in the report
            report_name: Name for the report (optional)
            
        Returns:
            Path to the generated report file
        """
        try:
            # Generate report name if not provided
            if not report_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_name = f"report_{timestamp}.html"
            
            # Create report content
            content = self._format_html_report(data)
            
            # Save report
            report_file = Path(self.reports_dir) / report_name
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return str(report_file)
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to generate HTML report: {str(e)}")
    
    def _format_html_report(self, data: Dict) -> str:
        """Format data as an HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Deep Cleaner Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; }}
        h2 {{ color: #666; }}
        .section {{ margin: 20px 0; }}
        .key {{ font-weight: bold; color: #333; }}
        .value {{ margin-left: 20px; }}
        .list-item {{ margin-left: 40px; }}
        .timestamp {{ color: #888; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Deep Cleaner Report</h1>
    <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    
    {self._format_html_section(data, 0)}
    
</body>
</html>
"""
        return html_content
    
    def _format_html_section(self, data: Dict, level: int) -> str:
        """Format a section as HTML."""
        html_content = ""
        
        for key, value in data.items():
            key_escaped = html.escape(str(key))
            if isinstance(value, dict):
                html_content += f"<div class='section'>\n"
                html_content += f"<h{level+2} class='key'>{key_escaped}:</h{level+2}>\n"
                html_content += self._format_html_section(value, level + 1)
                html_content += "</div>\n"
            elif isinstance(value, list):
                html_content += f"<div class='section'>\n"
                html_content += f"<h{level+2} class='key'>{key_escaped}:</h{level+2}>\n"
                html_content += "<ul>\n"
                for item in value:
                    if isinstance(item, dict):
                        html_content += "<li>\n"
                        html_content += self._format_html_section(item, level + 1)
                        html_content += "</li>\n"
                    else:
                        item_escaped = html.escape(str(item))
                        html_content += f"<li class='list-item'>{item_escaped}</li>\n"
                html_content += "</ul>\n"
                html_content += "</div>\n"
            else:
                value_escaped = html.escape(str(value))
                html_content += f"<div class='section'>\n"
                html_content += f"<div class='key'>{key_escaped}:</div>\n"
                html_content += f"<div class='value'>{value_escaped}</div>\n"
                html_content += "</div>\n"
        
        return html_content
    
    def generate_json_report(self, data: Dict, report_name: str = None) -> str:
        """Generate a JSON report.
        
        Args:
            data: Data to include in the report
            report_name: Name for the report (optional)
            
        Returns:
            Path to the generated report file
        """
        try:
            # Generate report name if not provided
            if not report_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_name = f"report_{timestamp}.json"
            
            # Add timestamp to data
            report_data = {
                "report_generated": datetime.now().isoformat(),
                "data": data
            }
            
            # Save report
            report_file = Path(self.reports_dir) / report_name
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            return str(report_file)
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to generate JSON report: {str(e)}")
    
    def generate_csv_report(self, data: Dict, report_name: str = None) -> str:
        """Generate a CSV report.
        
        Args:
            data: Data to include in the report (should be tabular data)
            report_name: Name for the report (optional)
            
        Returns:
            Path to the generated report file
        """
        try:
            # Generate report name if not provided
            if not report_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_name = f"report_{timestamp}.csv"
            
            # Save report
            report_file = Path(self.reports_dir) / report_name
            with open(report_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                if "headers" in data:
                    writer.writerow(data["headers"])
                
                # Write data rows
                if "rows" in data:
                    writer.writerows(data["rows"])
            
            return str(report_file)
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to generate CSV report: {str(e)}")
    
    def get_stats(self) -> dict:
        """Get statistics about reports."""
        try:
            reports_path = Path(self.reports_dir)
            report_files = list(reports_path.glob("report_*.*"))
            
            return {
                "total_reports": len(report_files),
                "reports_directory": self.reports_dir,
                "errors": self.error_count
            }
        except Exception:
            self.error_count += 1
            return {
                "total_reports": 0,
                "reports_directory": self.reports_dir,
                "errors": self.error_count
            }
    
    def list_reports(self) -> List[Dict]:
        """List all available reports."""
        try:
            reports_path = Path(self.reports_dir)
            reports = []
            
            for file in reports_path.glob("report_*.*"):
                try:
                    stat = file.stat()
                    reports.append({
                        "name": file.name,
                        "path": str(file),
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": file.suffix
                    })
                except Exception:
                    continue
            
            # Sort by modification time (newest first)
            reports.sort(key=lambda x: x["modified"], reverse=True)
            return reports
        except Exception:
            self.error_count += 1
            return []
    
    def delete_report(self, report_name: str) -> bool:
        """Delete a report.
        
        Args:
            report_name: Name of the report to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            report_file = Path(self.reports_dir) / report_name
            if report_file.exists():
                report_file.unlink()
                return True
            return False
        except Exception:
            self.error_count += 1
            return False