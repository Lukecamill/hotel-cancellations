"""Booking-time JSON HTTP service for local/container demonstration."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import signal
import threading
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from hotel_cancel.serving import Predictor

MAX_BODY = 65536
logger = logging.getLogger(__name__)


def make_server(predictor, host="127.0.0.1", port=8080, *, approvals=None, telemetry=None):
    if telemetry is None:
        from hotel_cancel.monitoring import Telemetry

        telemetry = Telemetry()
    review_token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def handle_one_request(self):
            started = time.perf_counter()
            self._status = None
            self._hotel = "unknown"
            try:
                return super().handle_one_request()
            finally:
                if self._status is not None:
                    telemetry.observe_request(
                        getattr(self, "path", "other"),
                        getattr(self, "command", "other"),
                        self._status,
                        self._hotel,
                        time.perf_counter() - started,
                    )

        def send_response(self, code, message=None):
            self._status = code
            return super().send_response(code, message)

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def respond(self, code, body):
            data = json.dumps(body, allow_nan=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

        def log_message(self, *_):
            pass  # Do not log booking payloads or arbitrary request paths.

        def do_GET(self):
            if self.path == "/metrics":
                from prometheus_client import CONTENT_TYPE_LATEST

                data = telemetry.render()
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if self.path in ("/", "/review"):
                data = (Path(__file__).parent / "web/review.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'",
                )
                self.end_headers()
                self.wfile.write(data)
                return
            if self.path == "/reviews":
                if approvals is None:
                    return self.respond(
                        503,
                        {"error": "Manager review requires a configured PostgreSQL connection"},
                    )
                try:
                    return self.respond(
                        200,
                        {
                            "csrf_token": review_token,
                            "reviews": approvals.list_reviews(),
                        },
                    )
                except Exception:
                    logger.exception("Review retrieval failed")
                    return self.respond(503, {"error": "Review database unavailable"})
            if self.path != "/health":
                return self.respond(404, {"error": "not_found"})
            self.respond(
                200,
                {
                    "status": "ready",
                    "model_version": predictor.version,
                    "service_version": os.environ.get("MODEL_VERSION", "dev"),
                    "diagnostic_gate": predictor.manifest["diagnostic_gate"],
                },
            )

        def do_POST(self):
            if self.path == "/reviews" or self.path.startswith("/reviews/"):
                return self.review_post()
            if self.path != "/predict":
                return self.respond(404, {"error": "not_found"})
            if self.headers.get_content_type() != "application/json":
                return self.respond(415, {"error": "application/json required"})
            if self.headers.get("Transfer-Encoding"):
                return self.respond(400, {"error": "Transfer-Encoding not supported"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    return self.respond(413, {"error": "body must be 1..65536 bytes"})
                data = self.rfile.read(length)
                if len(data) != length:
                    raise ValueError("Incomplete body")
                request = json.loads(
                    data,
                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON")),
                )
                if not isinstance(request, dict) or set(request) != {"booking"}:
                    raise ValueError("Expected one booking object")
                prob = float(predictor.predict([request["booking"]])[0])
                self._hotel = request["booking"]["hotel"]
                prediction_id, persisted = telemetry.prediction(request["booking"], prob, predictor.version)
            except (ValueError, TypeError, OverflowError, TimeoutError):
                return self.respond(422, {"error": "invalid_booking_request"})
            except Exception:
                logger.exception("Prediction failed")
                return self.respond(500, {"error": "prediction_failed"})
            self.respond(
                200,
                {
                    "cancellation_probability": prob,
                    "horizon": "booking_to_arrival",
                    "model_version": predictor.version,
                    "service_version": os.environ.get("MODEL_VERSION", "dev"),
                    "decision_authorised": False,
                    "prediction_id": prediction_id,
                    "prediction_logged": persisted,
                },
            )

        def review_post(self):
            if approvals is None:
                return self.respond(503, {"error": "Manager review database is not configured"})
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                return self.respond(403, {"error": "Cross-origin review request rejected"})
            supplied = self.headers.get("X-Review-Token", "")
            if not secrets.compare_digest(supplied, review_token):
                return self.respond(403, {"error": "Refresh the review page before submitting"})
            if self.headers.get_content_type() != "application/json":
                return self.respond(415, {"error": "application/json required"})
            if self.headers.get("Transfer-Encoding"):
                return self.respond(400, {"error": "Transfer-Encoding not supported"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    return self.respond(413, {"error": "Body must be 1..65536 bytes"})
                request = json.loads(self.rfile.read(length))
                if self.path == "/reviews":
                    if not isinstance(request, dict) or set(request) != {"snapshot_id"}:
                        raise ValueError("Provide one snapshot_id")
                    identifier = request["snapshot_id"]
                    if (
                        not isinstance(identifier, str)
                        or len(identifier) != 64
                        or any(x not in "0123456789abcdef" for x in identifier)
                    ):
                        raise ValueError("Snapshot ID must be a 64-character lowercase SHA-256 digest")
                    return self.respond(201, {"review_ids": approvals.publish(identifier, predictor)})
                parts = self.path.strip("/").split("/")
                if len(parts) != 3 or parts[0] != "reviews" or parts[2] != "decision":
                    return self.respond(404, {"error": "not_found"})
                return self.respond(201, approvals.decide(parts[1], request))
            except KeyError:
                return self.respond(404, {"error": "Review not found"})
            except ValueError as error:
                from hotel_cancel.approvals import DecisionConflict

                return self.respond(
                    409 if isinstance(error, DecisionConflict) else 422,
                    {"error": str(error)},
                )
            except (TypeError, TimeoutError):
                return self.respond(422, {"error": "Invalid review request"})
            except Exception:
                logger.exception("Review operation failed")
                return self.respond(503, {"error": "Review database operation failed"})

    return ThreadingHTTPServer((host, port), Handler)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", default=os.environ.get("SERVING_BUNDLE", "models/serving"))
    p.add_argument("--host", default=os.environ.get("SERVICE_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("SERVICE_PORT", "8080")))
    args = p.parse_args()
    predictor = Predictor(args.bundle)
    approvals = None
    if os.environ.get("DATABASE_URL"):
        from hotel_cancel.approvals import ApprovalStore

        approvals = ApprovalStore(os.environ["DATABASE_URL"])
    from hotel_cancel.monitoring import Telemetry

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    telemetry = Telemetry(os.environ.get("DATABASE_URL"))
    server = make_server(predictor, args.host, args.port, approvals=approvals, telemetry=telemetry)
    run_server(server)


def run_server(server):
    """Handle Docker's SIGTERM and finish without its ten-second kill timeout."""

    def stop(signum, frame):
        # shutdown() must run outside the thread executing serve_forever().
        threading.Thread(target=server.shutdown, daemon=True).start()

    previous = signal.signal(signal.SIGTERM, stop)
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    main()
