from __future__ import annotations

import logging
from typing import List
from logger_flow.agents.log_agents import TicketCreationAgent

logger = logging.getLogger(__name__)


def run_create(incidents: List[dict]) -> List[dict]:
    agent = TicketCreationAgent()
    try:
        tickets = agent.run(incidents)
        logger.info("create_tickets_task: created %d tickets", len(tickets))
        return tickets
    except Exception as e:
        logger.exception("create_tickets_task failed: %s", e)
        return []
