"""Unix domain socket transport: parse JSON line in, write JSON line out, delegate to orchestrator."""

import logging
import os
import signal
import socketserver
import threading
from pathlib import Path
from types import FrameType
from typing import cast, override

from pydantic import BaseModel, ValidationError

from encourage_gate.exceptions import BadRequestError
from encourage_gate.gate import default_gate
from encourage_gate.orchestrator import RewriteOrchestrator
from encourage_gate.protocol import ErrorResponse, RewriteRequest
from encourage_gate.rewriter import Rewriter
from encourage_gate.settings import AppSettings

log = logging.getLogger(__name__)


class EncourageHandler(socketserver.StreamRequestHandler):
    @property
    def _server(self) -> "EncourageServer":
        return cast(EncourageServer, self.server)

    @override
    def handle(self):
        try:
            request = self._read_request()
        except BadRequestError as err:
            self._write(ErrorResponse(error=str(err)))
            return
        if request is None:
            return
        response = self._server.orchestrator.apply(request.text)
        self._write(response)

    def _read_request(self) -> RewriteRequest | None:
        max_bytes = self._server.max_request_bytes
        raw = self.rfile.readline(max_bytes + 1)
        if len(raw) > max_bytes:
            raise BadRequestError(f"request exceeds {max_bytes} bytes")
        decoded = raw.decode("utf-8").strip()
        if not decoded:
            return None
        try:
            return RewriteRequest.model_validate_json(decoded)
        except ValidationError as err:
            raise BadRequestError(self._summarize_validation_error(err)) from err

    def _write(self, response: BaseModel):
        self.wfile.write((response.model_dump_json() + "\n").encode("utf-8"))

    @staticmethod
    def _summarize_validation_error(err: ValidationError) -> str:
        errors = err.errors()
        detail = errors[0]["msg"] if errors else "validation failed"
        return f"bad request: {detail}"


class EncourageServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        socket_path: Path,
        orchestrator: RewriteOrchestrator,
        *,
        max_request_bytes: int,
    ):
        socket_path.unlink(missing_ok=True)
        super().__init__(str(socket_path), EncourageHandler)
        os.chmod(socket_path, 0o600)
        self.orchestrator = orchestrator
        self.max_request_bytes = max_request_bytes
        self._socket_path = socket_path

    @override
    def server_close(self):
        super().server_close()
        self._socket_path.unlink(missing_ok=True)


def serve(settings: AppSettings | None = None):
    settings = settings or AppSettings()
    logging.basicConfig(level=settings.log_level)
    log.info("loading gate model (this takes a few seconds)...")
    rewriter = Rewriter(model=settings.model, timeout_seconds=settings.rewrite_timeout_seconds)
    orchestrator = RewriteOrchestrator(default_gate(), rewriter)
    log.info("listening on %s", settings.socket_path)
    with EncourageServer(
        settings.socket_path,
        orchestrator,
        max_request_bytes=settings.max_request_bytes,
    ) as server:
        _install_shutdown_handlers(server)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("shutting down")


def _install_shutdown_handlers(server: EncourageServer):
    def _handle(signum: int, _frame: FrameType | None):
        log.info("received signal %s, shutting down", signal.Signals(signum).name)
        threading.Thread(target=server.shutdown, daemon=True).start()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _handle)
