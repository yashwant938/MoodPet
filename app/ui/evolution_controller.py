"""One shared asynchronous progression feed for every pet view."""
import logging
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot


class _Result(QObject):
    ready = Signal(object)


class _Read(QRunnable):
    def __init__(self, db, result):
        super().__init__()
        self.db, self.result = db, result

    def run(self):
        try:
            self.result.ready.emit(self.db.get_evolution_snapshot(claim_unlocks=True))
        except Exception:
            logging.getLogger(__name__).warning('Progression read failed; next refresh will retry.')
            self.result.ready.emit(None)


class EvolutionController(QObject):
    changed = Signal(object)
    advanced = Signal(int)
    refresh_requested = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.snapshot = None
        self._running = self._pending = self._closed = False
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.result = _Result(self)
        self.result.ready.connect(self._received)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._read)
        self.refresh_requested.connect(self.request)
        self._notify = self.refresh_requested.emit
        db.subscribe_progress(self._notify)
        self.request()

    @Slot()
    def request(self):
        if self._closed:
            return
        if self._running:
            self._pending = True
        elif not self.timer.isActive():
            self.timer.start()

    def _read(self):
        if not self._closed:
            self._running = True
            self.pool.start(_Read(self.db, self.result))

    @Slot(object)
    def _received(self, snapshot):
        self._running = False
        if self._closed:
            return
        if snapshot is not None:
            self.snapshot = snapshot
            self.changed.emit(snapshot)
            if snapshot['advance']:
                self.advanced.emit(snapshot['advance'])
        if self._pending:
            self._pending = False
            self.request()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.timer.stop()
        self.db.unsubscribe_progress(self._notify)
        self.pool.waitForDone()
