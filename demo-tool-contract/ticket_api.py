"""
Mock enterprise ticket-system API.

This stands in for the "realistic enterprise API" from the lesson: it has
the quirks real APIs have (department scoping, status transitions, lookup by
ID) without needing any network or credentials.
"""

from dataclasses import dataclass, field


@dataclass
class Ticket:
    id: str
    title: str
    department: str
    status: str  # open | in_progress | resolved | closed
    priority: str  # low | medium | high | critical
    assignee: str = ""


class TicketAPI:
    VALID_TRANSITIONS = {
        "open": {"in_progress", "resolved"},
        "in_progress": {"resolved", "open"},
        "resolved": {"closed", "open"},
        "closed": set(),
    }

    def __init__(self):
        self._tickets = {
            "T-1001": Ticket("T-1001", "VPN tunnel drops hourly", "IT",
                             "open", "high"),
            "T-1002": Ticket("T-1002", "Expense report stuck in approval",
                             "Finance", "in_progress", "medium",
                             assignee="a.patel"),
            "T-1003": Ticket("T-1003", "New-hire laptop request", "IT",
                             "resolved", "low", assignee="j.chen"),
        }

    def get_ticket(self, ticket_id):
        return self._tickets.get(ticket_id)

    def search_tickets(self, department=None, status=None):
        out = list(self._tickets.values())
        if department:
            out = [t for t in out if t.department == department]
        if status:
            out = [t for t in out if t.status == status]
        return out

    def update_status(self, ticket_id, new_status):
        t = self._tickets.get(ticket_id)
        if t is None:
            raise KeyError(f"unknown ticket {ticket_id}")
        if new_status not in self.VALID_TRANSITIONS[t.status]:
            raise ValueError(
                f"illegal transition {t.status} -> {new_status}")
        t.status = new_status
        return t

    def create_ticket(self, title, department, priority):
        new_id = f"T-{1000 + len(self._tickets) + 1}"
        t = Ticket(new_id, title, department, "open", priority)
        self._tickets[new_id] = t
        return t
