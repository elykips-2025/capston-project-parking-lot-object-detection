import logging
import threading

from worker.processing_lease import renew_lease


logger = logging.getLogger(__name__)


class LeaseHeartbeat:
    """Renew a recording lease while inference is running."""

    def __init__(self, recording_id, token, interval_seconds=30):
        self.recording_id = recording_id
        self.token = token
        self.interval_seconds = interval_seconds

        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread = None

    @property
    def lost(self):
        return self._lost.is_set()

    def start(self):
        if self._thread is not None:
            raise RuntimeError("Heartbeat already started")

        self._thread = threading.Thread(
            target=self._run,
            name=f"lease-heartbeat-{self.recording_id}",
            daemon=True,
        )
        self._thread.start()

    def _run(self):
        while not self._stop.wait(self.interval_seconds):
            try:
                renewed = renew_lease(
                    self.recording_id,
                    self.token,
                )

                if not renewed:
                    logger.error(
                        "Lease ownership lost: %s",
                        self.recording_id,
                    )
                    self._lost.set()
                    return

            except Exception:
                logger.exception(
                    "Lease renewal failed: %s",
                    self.recording_id,
                )
                self._lost.set()
                return

    def stop(self):
        self._stop.set()

        if self._thread is not None:
            self._thread.join(timeout=10)

            if self._thread.is_alive():
                raise RuntimeError(
                    "Lease heartbeat did not stop cleanly"
                )
