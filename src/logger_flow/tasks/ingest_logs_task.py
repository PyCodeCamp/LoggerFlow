from __future__ import annotations

import logging
from typing import List
from logger_flow.agents.log_agents import LogIngestionAgent
from logger_flow.tools import LogEntry

logger = logging.getLogger(__name__)


def run_ingest(log_dir: str | None = None) -> List[LogEntry]:
    agent = LogIngestionAgent(log_dir=log_dir)
    try:
        entries = agent.run()
        logger.info("ingest_logs_task: returned %d entries", len(entries))
        return entries
    except Exception as e:
        logger.exception("ingest_logs_task failed: %s", e)
        return []
