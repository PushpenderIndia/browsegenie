import threading
import uuid
from typing import Dict, List, Optional

from .runner import BrowserAgent

_sessions: Dict[str, "BrowserAgentSession"] = {}


class BrowserAgentSession:
    def __init__(self, agent: BrowserAgent):
        self.session_id: str = str(uuid.uuid4())
        self._agent = agent
        self._thread: Optional[threading.Thread] = None
        self.done = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self._agent.run()
        finally:
            self.done.set()

    @property
    def event_queue(self):
        return self._agent.event_queue

    @property
    def is_done(self) -> bool:
        return self.done.is_set()

    def get_playback_frames(self) -> List[dict]:
        return self._agent.recorder.to_list()

    def stop(self) -> None:
        self._agent.stop()
        self.done.set()


def create_session(
    task: str,
    model: str,
    provider: str = "",
    api_key: str = "",
    headless: bool = True,
) -> BrowserAgentSession:
    agent = BrowserAgent(
        task=task,
        model=model,
        provider=provider,
        api_key=api_key,
        headless=headless,
    )
    session = BrowserAgentSession(agent)
    _sessions[session.session_id] = session
    session.start()
    return session


def get_session(session_id: str) -> Optional[BrowserAgentSession]:
    return _sessions.get(session_id)
