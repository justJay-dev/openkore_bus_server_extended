"""
Template rendering support for the OpenKore Bus server
Provides Jinja2 template rendering functionality
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    Environment = None
    FileSystemLoader = None


class TemplateRenderer:
    """Handles template rendering using Jinja2."""

    def __init__(self, template_dir: str = "templates"):
        if not JINJA2_AVAILABLE:
            raise ImportError("Jinja2 is not installed. Run: pip install jinja2")

        self.template_dir = template_dir
        self.start_time = time.time()

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        self.env.filters["format_uptime"] = self._format_uptime
        self.env.filters["format_datetime"] = self._format_datetime

    def render_template(self, template_name: str, **context: Any) -> str:
        """Render a template with the given context."""
        template = self.env.get_template(template_name)

        # Add common context variables
        common_context = {
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_timestamp": int(time.time()),
            "server_start_time": self.start_time,
            "uptime_seconds": int(time.time() - self.start_time),
        }

        # Merge contexts (passed context overrides common)
        full_context = {**common_context, **context}

        return template.render(**full_context)

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in seconds to a human-readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _format_datetime(
        self, timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> str:
        """Format a timestamp to a datetime string."""
        return datetime.fromtimestamp(timestamp).strftime(format_str)

    def template_exists(self, template_name: str) -> bool:
        """Check if a template file exists."""
        try:
            self.env.get_template(template_name)
            return True
        except:
            return False


def get_template_renderer(
    template_dir: Optional[str] = None,
) -> Optional[TemplateRenderer]:
    """Get a template renderer instance, or None if Jinja2 is not available."""
    if not JINJA2_AVAILABLE:
        return None

    if template_dir is None:
        # Default template directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(os.path.dirname(current_dir), "templates")

    if not os.path.exists(template_dir):
        return None

    try:
        return TemplateRenderer(template_dir)
    except Exception:
        return None
