"""Persistent solver job status, independent of browser polling lifetime."""

from __future__ import annotations

import copy
import re
import threading
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from dashboard.planner import PlanStore

Worker = Callable[[dict[str, Any]], dict[str, Any]]


class PlannerJobs:
    _lock = threading.RLock()
    _threads: dict[str, threading.Thread] = {}

    def __init__(self, directory: Path) -> None:
        self.directory = directory.resolve()

    def _store(self, job_id: str) -> PlanStore:
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise ValueError("Invalid job identifier.")
        return PlanStore(self.directory / f"{job_id}.json")

    def status(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            store = self._store(job_id)
            state = store.load()
            if state is None:
                raise ValueError("Job record missing. Last saved plan remains available; retry solve.")
            thread = self._threads.get(str(store.path))
            if state["status"] == "running" and (thread is None or not thread.is_alive()):
                state.update(status="interrupted", error="Worker stopped. Last saved plan retained; retry solve.")
                store.save(state)
            return state

    def start(self, request: dict[str, Any], worker: Worker) -> str:
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            for path in self.directory.glob("*.json"):
                if re.fullmatch(r"[a-f0-9]{32}", path.stem):
                    previous = self.status(path.stem)
                    if previous["status"] == "running":
                        raise ValueError("A planner job is already running. Wait for it to finish.")
                    if (request.get("kind") == "solve" and previous["status"] == "finished"
                            and previous["request"].get("snapshot") == request.get("snapshot")
                            and previous["request"].get("source_digest") == request.get("source_digest")
                            and not previous["result"].get("errors")):
                        return path.stem
            job_id = uuid4().hex
            store = self._store(job_id)
            store.save({"id": job_id, "status": "running", "request": copy.deepcopy(request),
                        "result": None, "error": None})

            def run() -> None:
                try:
                    result = worker(copy.deepcopy(request))
                    state = {"id": job_id, "status": "finished", "request": request,
                             "result": result, "error": None}
                except Exception as exc:
                    state = {"id": job_id, "status": "failed", "request": request,
                             "result": None, "error": str(exc)}
                with self._lock:
                    store.save(state)

            thread = threading.Thread(target=run, name=f"planner-{job_id}", daemon=True)
            self._threads[str(store.path)] = thread
            thread.start()
            return job_id

    def wait(self, job_id: str, timeout: float) -> dict[str, Any]:
        thread = self._threads.get(str(self._store(job_id).path))
        if thread is not None:
            thread.join(timeout)
        return self.status(job_id)
