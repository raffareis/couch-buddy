"""Observa a pasta de saves e dispara callback quando um .zks fica estável.

O jogo escreve o .zks em chunks; o callback só dispara depois que o arquivo
para de mudar por ``debounce_s`` segundos.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class _Handler(FileSystemEventHandler):
    def __init__(self, watcher: "SaveWatcher") -> None:
        self._watcher = watcher

    def on_created(self, event: FileSystemEvent) -> None:
        self._touch(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._touch(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        if str(event.dest_path).endswith(".zks"):
            self._watcher._schedule(Path(str(event.dest_path)))

    def _touch(self, event: FileSystemEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".zks"):
            self._watcher._schedule(Path(str(event.src_path)))


class SaveWatcher:
    def __init__(
        self,
        saves_dir: Path,
        on_save: Callable[[Path], None],
        debounce_s: float = 2.0,
    ) -> None:
        self._saves_dir = saves_dir
        self._on_save = on_save
        self._debounce_s = debounce_s
        self._timers: dict[Path, threading.Timer] = {}
        self._lock = threading.Lock()
        self._observer = Observer()
        self._observer.schedule(_Handler(self), str(saves_dir), recursive=False)

    def _schedule(self, path: Path) -> None:
        with self._lock:
            if timer := self._timers.pop(path, None):
                timer.cancel()
            timer = threading.Timer(self._debounce_s, self._fire, args=(path,))
            timer.daemon = True
            self._timers[path] = timer
            timer.start()

    def _fire(self, path: Path) -> None:
        with self._lock:
            self._timers.pop(path, None)
        if path.exists():
            self._on_save(path)

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
        self._observer.join(timeout=5)
