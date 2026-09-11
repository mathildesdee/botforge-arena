"""Dev-only stub for the robot validation endpoint
(docs/ARCHITECTURE.md #4), so the upload UI can be built and tested
before the real backend "[Backend] Robot JSON schema validation"
issue lands. This is not the real validator — just enough logic to
exercise both the success and failure paths in the browser. Delete
once the real backend endpoint exists, or keep as a frontend fixture.

Usage:
    python3 mock_validate_server.py
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8766
BUILD_KEYS = ("speed", "armor", "weapon_power", "accuracy", "fire_rate", "sensor_range")
MAX_BUILD_POINTS = 100


def validate_robot(robot):
    errors = []

    name = robot.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append({"field": "name", "message": "Robot name is required."})

    build = robot.get("build")
    if not isinstance(build, dict):
        errors.append({"field": "build", "message": "Build is required and must be an object."})
        return errors

    for key in build:
        if key not in BUILD_KEYS:
            errors.append({"field": f"build.{key}", "message": f"Unknown build stat '{key}'."})

    total = sum(v for v in build.values() if isinstance(v, (int, float)))
    if total > MAX_BUILD_POINTS:
        errors.append(
            {
                "field": "build",
                "message": f"Build points sum to {total}; the maximum is {MAX_BUILD_POINTS}.",
            }
        )

    return errors


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/robots/validate":
            self._send_json(404, {"valid": False, "errors": [{"message": "Not found."}]})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            robot = json.loads(raw)
        except json.JSONDecodeError as err:
            self._send_json(400, {"valid": False, "errors": [{"message": f"Invalid JSON: {err}"}]})
            return

        errors = validate_robot(robot)
        if errors:
            self._send_json(422, {"valid": False, "errors": errors})
        else:
            self._send_json(200, {"valid": True, "robot": robot})

    def log_message(self, format, *args):
        pass  # keep the console quiet — this is a throwaway dev stub


if __name__ == "__main__":
    print(f"Mock robot validation server running at http://localhost:{PORT}/api/robots/validate")
    HTTPServer(("localhost", PORT), Handler).serve_forever()
