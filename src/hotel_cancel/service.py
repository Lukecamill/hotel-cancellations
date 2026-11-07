"""Booking-time JSON HTTP service for local/container demonstration."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import signal
import threading

from hotel_cancel.serving import Predictor

MAX_BODY = 65536
logger = logging.getLogger(__name__)


def make_server(predictor, host='127.0.0.1', port=8080):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def respond(self, code, body):
            data = json.dumps(body, allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

        def log_message(self, *_):
            pass  # Do not log booking payloads or arbitrary request paths.

        def do_GET(self):
            if self.path != '/health':
                return self.respond(404, {'error': 'not_found'})
            self.respond(200, {'status': 'ready', 'model_version': predictor.version,
                               'diagnostic_gate': predictor.manifest['diagnostic_gate']})

        def do_POST(self):
            if self.path != '/predict':
                return self.respond(404, {'error': 'not_found'})
            if self.headers.get_content_type() != 'application/json':
                return self.respond(415, {'error': 'application/json required'})
            if self.headers.get('Transfer-Encoding'):
                return self.respond(400, {'error': 'Transfer-Encoding not supported'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY:
                    return self.respond(413, {'error': 'body must be 1..65536 bytes'})
                data = self.rfile.read(length)
                if len(data) != length:
                    raise ValueError('Incomplete body')
                request = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON')))
                if not isinstance(request, dict) or set(request) != {'booking'}:
                    raise ValueError('Expected one booking object')
                prob = float(predictor.predict([request['booking']])[0])
            except (ValueError, TypeError, OverflowError, TimeoutError):
                return self.respond(422, {'error': 'invalid_booking_request'})
            except Exception:
                logger.exception('Prediction failed')
                return self.respond(500, {'error': 'prediction_failed'})
            self.respond(200, {'cancellation_probability': prob, 'horizon': 'booking_to_arrival',
                              'model_version': predictor.version, 'decision_authorised': False})
    return ThreadingHTTPServer((host, port), Handler)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', default=os.environ.get('SERVING_BUNDLE', 'models/serving'))
    p.add_argument('--host', default=os.environ.get('SERVICE_HOST', '127.0.0.1'))
    p.add_argument('--port', type=int, default=int(os.environ.get('SERVICE_PORT', '8080')))
    args = p.parse_args()
    predictor = Predictor(args.bundle)
    server = make_server(predictor, args.host, args.port)
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


if __name__ == '__main__':
    main()
