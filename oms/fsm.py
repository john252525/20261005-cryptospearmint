"""Order state machine — explicit, testable."""
from __future__ import annotations
from typing import Final

TRANSITIONS: Final = {
    "NEW":     {"ORDER_ACKNOWLEDGED", "ORDER_REJECTED"},
    "ACK":     {"ORDER_PARTIALLY_FILLED", "ORDER_FILLED",
                "ORDER_CANCELED", "ORDER_REJECTED"},
    "PARTIAL": {"ORDER_PARTIALLY_FILLED", "ORDER_FILLED", "ORDER_CANCELED"},
    "FILLED":  set(),
    "REJECTED": set(),
    "CANCELED": set(),
}

TERMINAL: Final = frozenset({"FILLED", "REJECTED", "CANCELED"})

_EVT2ST = {
    "ORDER_ACKNOWLEDGED":     "ACK",
    "ORDER_PARTIALLY_FILLED": "PARTIAL",
    "ORDER_FILLED":           "FILLED",
    "ORDER_REJECTED":         "REJECTED",
    "ORDER_CANCELED":         "CANCELED",
}


class InvalidTransition(Exception):
    """Raised when an event cannot be applied to the current status."""


def next_status(current: str, event_type: str) -> str:
    allowed = TRANSITIONS.get(current)
    if allowed is None:
        raise InvalidTransition(f"unknown status: {current}")
    if event_type not in allowed:
        raise InvalidTransition(f"cannot apply {event_type} from {current}")
    return _EVT2ST[event_type]


def is_terminal(status: str) -> bool:
    return status in TERMINAL
