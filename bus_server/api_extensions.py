"""
API extensions for the OpenKore Bus server
Demonstrates how to add REST API functionality with template support
"""

import asyncio
import json
import time
from typing import Dict, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from urllib.parse import urlparse, parse_qs

from .main_server import MainServer
from .template_renderer import get_template_renderer


class BusAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for bus server endpoints with template support."""

    def __init__(self, bus_server: MainServer, *args, **kwargs):
        self.bus_server = bus_server
        self.template_renderer = get_template_renderer()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        # Template routes
        if path == "/" or path == "/status":
            self._handle_status_page()
        elif path == "/api_docs" or path == "/docs":
            self._handle_api_docs_page()
        elif path == "/broadcast":
            self._handle_broadcast_page()
        elif path == "/admin":
            self._handle_admin_page()
        # API routes
        elif path == "/api/status":
            self._handle_status()
        elif path == "/bc":
            self._handle_broadcast_get(query_params)
        else:
            self._send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/api/broadcast":
            self._handle_broadcast()
        elif path == "/api/message":
            self._handle_message()
        else:
            self._send_error(404, "Not Found")

    def _handle_status(self):
        """Return server status."""
        status = {
            "running": self.bus_server.running,
            "host": self.bus_server.host,
            "port": self.bus_server.port,
            "client_count": len(self.bus_server.clients),
        }
        self._send_json_response(status)

    def _handle_status_page(self):
        """Render status page using template."""
        if not self.template_renderer:
            self._send_error(500, "Template rendering not available")
            return

        try:
            # Get uptime
            uptime = None
            if hasattr(self.bus_server, "_event_loop") and hasattr(
                self.template_renderer, "start_time"
            ):
                uptime_seconds = int(time.time() - self.template_renderer.start_time)
                uptime = self.template_renderer._format_uptime(uptime_seconds)

            # Get client information
            clients = []
            for client in self.bus_server.clients.values():
                clients.append(
                    {
                        "client_id": client.client_id,
                        "name": client.name,
                        "state": client.state,
                    }
                )

            # Get API port
            api_port = getattr(self.bus_server, "api_port", "N/A")

            context = {
                "server_running": self.bus_server.running,
                "server_host": self.bus_server.host,
                "server_port": self.bus_server.port,
                "client_count": len(self.bus_server.clients),
                "clients": clients,
                "api_port": api_port,
                "uptime": uptime,
            }

            html_content = self.template_renderer.render_template(
                "status.html", **context
            )
            self._send_html_response(html_content)
        except Exception as e:
            self._send_error(500, f"Template rendering failed: {str(e)}")

    def _handle_api_docs_page(self):
        """Render API documentation page using template."""
        if not self.template_renderer:
            self._send_error(500, "Template rendering not available")
            return

        try:
            html_content = self.template_renderer.render_template("api_docs.html")
            self._send_html_response(html_content)
        except Exception as e:
            self._send_error(500, f"Template rendering failed: {str(e)}")

    def _handle_broadcast_page(self):
        """Render broadcast interface page using template."""
        if not self.template_renderer:
            self._send_error(500, "Template rendering not available")
            return

        try:
            context = {"client_count": len(self.bus_server.clients)}
            html_content = self.template_renderer.render_template(
                "broadcast.html", **context
            )
            self._send_html_response(html_content)
        except Exception as e:
            self._send_error(500, f"Template rendering failed: {str(e)}")

    def _handle_admin_page(self):
        """Render admin interface page using template."""
        if not self.template_renderer:
            self._send_error(500, "Template rendering not available")
            return

        try:
            import sys

            # Get total connections (this could be tracked as a counter)
            total_connections = len(
                self.bus_server.clients
            )  # Current, but could be historical

            # Get API port
            api_port = getattr(self.bus_server, "api_port", "N/A")

            # Get uptime
            uptime = None
            if hasattr(self.template_renderer, "start_time"):
                uptime_seconds = int(time.time() - self.template_renderer.start_time)
                uptime = self.template_renderer._format_uptime(uptime_seconds)

            context = {
                "server_host": self.bus_server.host,
                "server_port": self.bus_server.port,
                "api_port": api_port,
                "client_count": len(self.bus_server.clients),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "total_connections": total_connections,
                "uptime": uptime,
                "quiet_mode": getattr(self.bus_server, "quiet", False),
            }

            html_content = self.template_renderer.render_template(
                "admin.html", **context
            )
            self._send_html_response(html_content)
        except Exception as e:
            self._send_error(500, f"Template rendering failed: {str(e)}")

    def _handle_broadcast_get(self, query_params: Dict):
        """Handle broadcast message via GET request with query parameters."""
        try:
            # Extract parameters from query
            player = query_params.get("player", [""])[0]
            comm = query_params.get("comm", [""])[0]

            if not player or not comm:
                self._send_error(400, "Missing required parameters: player and comm")
                return

            # Build message arguments - keep OpenKore format
            # Normalize "all" for OpenKore compatibility
            target_player = player
            if player.upper() in ["ALL", "*", "EVERYONE", "BROADCAST"]:
                target_player = "all"  # OpenKore expects lowercase "all"

            args = {"player": target_player, "comm": comm}

            # Add any additional query parameters
            for key, values in query_params.items():
                if key not in ["player", "comm", "type"] and values:
                    args[key] = values[0]

            message_id = "busComm"  # Use OpenKore standard message ID

            # Log the API call
            if not self.bus_server.quiet:
                print(
                    f"🌐 API Request: player='{player}', target_player='{target_player}', comm='{comm}', message_id='{message_id}'"
                )
                print(f"📤 Sending args: {args}")

            # Schedule the message send in the event loop
            try:
                # Get the event loop from the main thread
                if (
                    hasattr(self.bus_server, "_event_loop")
                    and self.bus_server._event_loop
                ):
                    loop = self.bus_server._event_loop
                else:
                    # Fallback: try to get the running loop
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        # Create a new event loop if none exists
                        print(
                            "⚠️ No running event loop found, creating a new one for message"
                        )
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                # Always broadcast the message - let clients decide if they should execute it
                # This matches OpenKore's bus behavior where all messages are broadcast
                future = asyncio.run_coroutine_threadsafe(
                    self.bus_server.broadcast(message_id, args), loop
                )
                future.result(timeout=2.0)  # Wait up to 2 seconds

                client_count = len(
                    [
                        c
                        for c in self.bus_server.clients.values()
                        if c.state == self.bus_server.IDENTIFIED
                    ]
                )

                if player.upper() in ["ALL", "*", "EVERYONE", "BROADCAST"]:
                    response = {
                        "status": "success",
                        "message": "Message broadcasted to all clients",
                        "message_id": message_id,
                        "args": args,
                        "client_count": client_count,
                        "target": "broadcast",
                    }

                    if not self.bus_server.quiet:
                        print(f"📡 API broadcast sent to {client_count} clients")
                else:
                    response = {
                        "status": "success",
                        "message": f"Message sent to player '{target_player}' (broadcasted to {client_count} clients)",
                        "message_id": message_id,
                        "args": args,
                        "client_count": client_count,
                        "target": target_player,
                    }

                    if not self.bus_server.quiet:
                        print(
                            f"📨 API message for '{target_player}' broadcasted to {client_count} clients"
                        )

                self._send_json_response(response)

            except asyncio.TimeoutError:
                self._send_error(500, "Broadcast timeout")
            except Exception as e:
                self._send_error(500, f"Broadcast failed: {str(e)}")

        except Exception as e:
            self._send_error(400, f"Bad Request: {str(e)}")

    def _handle_broadcast(self):
        """Handle broadcast message via API."""
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8"))

            message_id = data.get("message_id", "API_BROADCAST")
            args = data.get("args", {})

            # Schedule the broadcast in the event loop
            asyncio.run_coroutine_threadsafe(
                self.bus_server.broadcast(message_id, args), asyncio.get_event_loop()
            )

            self._send_json_response({"status": "sent", "message_id": message_id})

        except Exception as e:
            self._send_error(400, f"Bad Request: {str(e)}")

    def _handle_message(self):
        """Handle private message via API."""
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8"))

            client_id = data.get("client_id")
            message_id = data.get("message_id", "API_MESSAGE")
            args = data.get("args", {})

            if not client_id:
                self._send_error(400, "client_id required")
                return

            # Schedule the message send in the event loop
            future = asyncio.run_coroutine_threadsafe(
                self.bus_server.send_to_client(client_id, message_id, args),
                (
                    self.bus_server._event_loop
                    if hasattr(self.bus_server, "_event_loop")
                    else asyncio.get_event_loop()
                ),
            )

            success = future.result(timeout=1.0)

            if success:
                self._send_json_response({"status": "sent", "client_id": client_id})
            else:
                self._send_error(404, "Client not found")

        except Exception as e:
            self._send_error(400, f"Bad Request: {str(e)}")

    def _send_json_response(self, data: Dict):
        """Send JSON response."""
        response = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response)

    def _send_html_response(self, html_content: str):
        """Send HTML response."""
        response = html_content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _send_error(self, code: int, message: str):
        """Send error response."""
        error_response = {"error": message, "code": code}
        response = json.dumps(error_response).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response)


class BusServerWithAPI(MainServer):
    """Extended bus server with REST API functionality."""

    def __init__(
        self,
        port: int = 0,
        bind: str = "localhost",
        quiet: bool = False,
        api_port: Optional[int] = None,
    ):
        super().__init__(port, bind, quiet)
        self.api_port = api_port or (port + 1000) if port > 0 else 9080
        self.api_server: Optional[HTTPServer] = None
        self.api_thread: Optional[threading.Thread] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> None:
        """Start the bus server and API server."""
        # Store the event loop reference for API handler
        self._event_loop = asyncio.get_running_loop()
        await super().start()
        self._start_api_server()

    async def shutdown(self) -> None:
        """Shutdown both servers."""
        self._stop_api_server()
        await super().shutdown()

    def _start_api_server(self) -> None:
        """Start the REST API server in a separate thread."""
        if not self.quiet:
            print(f"🌐 Starting API server on {self.host}:{self.api_port}")

        def handler_factory(*args, **kwargs):
            return BusAPIHandler(self, *args, **kwargs)

        # Use the same host as the main server
        self.api_server = HTTPServer((self.host, self.api_port), handler_factory)
        self.api_thread = threading.Thread(target=self.api_server.serve_forever)
        self.api_thread.daemon = True
        self.api_thread.start()

    def _stop_api_server(self) -> None:
        """Stop the REST API server."""
        if self.api_server:
            self.api_server.shutdown()
            self.api_server.server_close()

        if self.api_thread and self.api_thread.is_alive():
            self.api_thread.join(timeout=5.0)
