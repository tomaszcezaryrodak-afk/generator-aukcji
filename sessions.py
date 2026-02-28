"""
Zarządzanie sesjami użytkowników (in-memory store).

Każda sesja = token UUID4 + dane stanu (limity API, wyniki generowania, kolejka SSE).
TTL 24h, cleanup co 1h.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field

SESSION_TTL = 24 * 3600  # 24h
CLEANUP_INTERVAL = 3600  # 1h
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 min
SSE_TICKET_TTL = 30  # 30s, jednorazowy


@dataclass
class SessionData:
    token: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    # API counters
    api_calls_count: int = 0
    image_gen_count: int = 0
    text_gen_count: int = 0
    # Generation job
    job_id: str | None = None
    job_status: str = "idle"  # idle | running | done | error
    job_progress: float = 0.0
    job_message: str = ""
    job_error: str = ""
    # Results (file paths on disk)
    results_dir: str = ""
    results_images: dict = field(default_factory=dict)  # key -> file path
    results_sections: dict = field(default_factory=dict)
    results_desc_raw: str = ""
    results_timestamp: str = ""
    # Source images (file paths)
    source_image_paths: list = field(default_factory=list)
    # Generation config (for chat edits)
    last_catalog: str = ""
    last_kategoria: str = ""
    last_kolory: dict = field(default_factory=dict)
    last_auto_draft_id: str | None = None
    # Analysis (nowy flow: analyze -> confirm -> generate)
    last_analysis: dict = field(default_factory=dict)
    # Chat state
    image_chat_history: dict = field(default_factory=dict)
    description_revisions: list = field(default_factory=list)
    desc_chat_history: list = field(default_factory=list)
    regen_count: int = 0
    # SSE queue
    sse_queue: asyncio.Queue | None = None
    # --- Pipeline v3.0: Fazy ---
    current_phase: str = "idle"  # idle | dna | phase1 | phase1_approval | phase2 | phase2_approval | finalizing | done
    phase_event: asyncio.Event | None = None
    phase_feedback: str = ""
    phase_round: int = 0
    phase_approved: bool = False
    # Transparent images (po rembg)
    transparent_images: dict = field(default_factory=dict)  # name -> file_path
    # Product DNA (JSON z Gemini TEXT)
    product_dna: dict = field(default_factory=dict)
    product_dna_corrected: bool = False
    # Approved packshots (po Fazie 1)
    approved_packshots: dict = field(default_factory=dict)  # key -> file_path
    # Generation mode
    generation_mode: str = "interactive"  # interactive | batch
    # Cancel flag (sprawdzane przez _run_generation)
    cancel_requested: bool = False
    # Koszty per model (tracking)
    model_costs: dict = field(default_factory=dict)  # model_name -> total_usd
    total_cost_usd: float = 0.0


@dataclass
class LockoutTracker:
    attempts: int = 0
    lockout_until: float = 0.0


@dataclass
class SSETicket:
    session_token: str
    created_at: float = field(default_factory=time.time)


# In-memory stores
sessions: dict[str, SessionData] = {}
lockouts: dict[str, LockoutTracker] = {}  # IP -> tracker
sse_tickets: dict[str, SSETicket] = {}  # ticket_id -> SSETicket


class TooManySessions(Exception):
    pass


def create_session(max_sessions: int = 5) -> SessionData:
    # Enforce concurrent session limit
    cleanup_expired()
    if len(sessions) >= max_sessions:
        raise TooManySessions(f"Limit sesji ({max_sessions}) osiagniety")
    token = uuid.uuid4().hex
    session = SessionData(token=token)
    sessions[token] = session
    return session


def get_session(token: str) -> SessionData | None:
    session = sessions.get(token)
    if session is None:
        return None
    if time.time() - session.created_at > SESSION_TTL:
        sessions.pop(token, None)
        return None
    session.last_activity = time.time()
    return session


def cleanup_expired():
    now = time.time()
    expired = [t for t, s in sessions.items() if now - s.created_at > SESSION_TTL]
    for t in expired:
        sessions.pop(t, None)
    expired_locks = [ip for ip, lk in lockouts.items()
                     if lk.lockout_until < now and lk.attempts == 0]
    for ip in expired_locks:
        lockouts.pop(ip, None)


def check_lockout(ip: str) -> int:
    """Zwraca pozostałe sekundy blokady, 0 jeśli nie zablokowany."""
    tracker = lockouts.get(ip)
    if not tracker:
        return 0
    remaining = tracker.lockout_until - time.time()
    if remaining <= 0:
        tracker.attempts = 0
        tracker.lockout_until = 0.0
        return 0
    return int(remaining)


def record_failed_login(ip: str):
    tracker = lockouts.setdefault(ip, LockoutTracker())
    tracker.attempts += 1
    if tracker.attempts >= MAX_LOGIN_ATTEMPTS:
        tracker.lockout_until = time.time() + LOCKOUT_DURATION


def reset_lockout(ip: str):
    lockouts.pop(ip, None)


def create_sse_ticket(session_token: str) -> str:
    """Tworzy jednorazowy ticket do SSE (30s TTL). Token sesji NIE trafia do URL."""
    _cleanup_expired_tickets()
    ticket_id = uuid.uuid4().hex
    sse_tickets[ticket_id] = SSETicket(session_token=session_token)
    return ticket_id


def validate_sse_ticket(ticket_id: str) -> SessionData | None:
    """Waliduje i KASUJE ticket (one-time use). Zwraca sesje lub None."""
    ticket = sse_tickets.pop(ticket_id, None)
    if ticket is None:
        return None
    if time.time() - ticket.created_at > SSE_TICKET_TTL:
        return None
    return get_session(ticket.session_token)


def _cleanup_expired_tickets():
    """Usuwa przeterminowane tickety."""
    now = time.time()
    expired = [tid for tid, t in sse_tickets.items()
               if now - t.created_at > SSE_TICKET_TTL]
    for tid in expired:
        sse_tickets.pop(tid, None)
