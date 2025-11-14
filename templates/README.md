# Template Support Documentation

The OpenKore Bus Server Extended now supports Jinja2 templates for rendering dynamic web pages.

## Overview

Template support allows you to create custom web interfaces for monitoring and controlling your bus server. The system uses Jinja2 templating engine to render HTML pages with dynamic content.

## Requirements

-   Python 3.7+
-   Jinja2 3.0.0+

Install with:

```bash
pip install jinja2
```

## Template Directory Structure

```
templates/
├── base.html          # Base template with common layout
├── status.html        # Server status page
├── api_docs.html      # API documentation page
├── broadcast.html     # Broadcast interface page
├── admin.html         # Admin interface page
└── [custom].html      # Your custom templates
```

## Available Routes

-   `/` or `/status` - Server status dashboard
-   `/docs` or `/api_docs` - API documentation
-   `/broadcast` - Broadcast message interface
-   `/admin` - Administration panel
-   `/api/status` - JSON status endpoint
-   `/bc` - Broadcast via GET parameters

## Template Context Variables

All templates have access to these common variables:

-   `current_time` - Current timestamp as formatted string
-   `current_timestamp` - Current Unix timestamp
-   `server_start_time` - Server start time (Unix timestamp)
-   `uptime_seconds` - Server uptime in seconds

### Status Page Context

-   `server_running` - Boolean, server running status
-   `server_host` - Server host address
-   `server_port` - Server port
-   `client_count` - Number of connected clients
-   `clients` - List of client objects with `client_id`, `name`, `state`
-   `api_port` - API server port
-   `uptime` - Formatted uptime string

### Admin Page Context

-   All status page variables plus:
-   `python_version` - Python version string
-   `total_connections` - Total connection count
-   `quiet_mode` - Boolean, quiet mode status

### Broadcast Page Context

-   `client_count` - Number of connected clients

## Creating Custom Templates

1. Create a new `.html` file in the `templates/` directory
2. Extend the base template:

    ```html
    {% extends "base.html" %} {% block title %}My Page - {{ super() }}{%
    endblock %} {% block content %}
    <h2>My Custom Page</h2>
    <p>Server has {{ client_count }} clients connected.</p>
    {% endblock %}
    ```

3. Add a route handler in `api_extensions.py`:

    ```python
    def _handle_my_page(self):
        """Render my custom page."""
        if not self.template_renderer:
            self._send_error(500, "Template rendering not available")
            return

        try:
            context = {
                'client_count': len(self.bus_server.clients),
                'custom_data': 'Hello World'
            }
            html_content = self.template_renderer.render_template('my_page.html', **context)
            self._send_html_response(html_content)
        except Exception as e:
            self._send_error(500, f"Template rendering failed: {str(e)}")
    ```

4. Add the route to `do_GET()`:
    ```python
    elif path == "/my_page":
        self._handle_my_page()
    ```

## Template Features

### Base Template Blocks

-   `{% block title %}` - Page title
-   `{% block extra_head %}` - Additional head content (CSS, meta tags)
-   `{% block header %}` - Page header
-   `{% block subtitle %}` - Page subtitle
-   `{% block content %}` - Main page content
-   `{% block scripts %}` - JavaScript code

### Custom Filters

-   `format_uptime` - Format seconds to human-readable uptime
-   `format_datetime` - Format Unix timestamp to datetime string

### Example Usage

```html
{% extends "base.html" %} {% block content %}
<p>Server uptime: {{ uptime_seconds | format_uptime }}</p>
<p>Started: {{ server_start_time | format_datetime }}</p>
{% endblock %}
```

## Styling

The base template includes responsive CSS with:

-   Clean, modern design
-   Grid layouts for cards and info displays
-   Button styles for actions
-   Dark code blocks for syntax highlighting
-   Auto-refresh functionality

## Security Considerations

-   Templates are rendered server-side with auto-escaping enabled
-   HTML/XML content is automatically escaped to prevent XSS
-   Only trusted template files should be placed in the templates directory

## Troubleshooting

### Template Not Found Error

-   Ensure the template file exists in the `templates/` directory
-   Check file permissions
-   Verify the template name is correct

### Jinja2 Import Error

-   Install Jinja2: `pip install jinja2`
-   Ensure Python can import the module

### Template Rendering Error

-   Check template syntax
-   Verify all referenced variables exist in context
-   Check server logs for detailed error information

## Examples

See the included templates for examples of:

-   Server monitoring dashboards
-   API documentation
-   Interactive forms
-   Real-time data display
-   Administration interfaces
