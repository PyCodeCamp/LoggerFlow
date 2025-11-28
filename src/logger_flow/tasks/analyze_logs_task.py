from __future__ import annotations

import logging
from typing import List
from logger_flow.agents.log_agents import LogAnalysisAgent
from logger_flow.tools import LogEntry

logger = logging.getLogger(__name__)


def run_analyze(entries: List[LogEntry]) -> List[dict]:
    agent = LogAnalysisAgent()
    try:
        incidents = agent.run(entries)
        logger.info("analyze_logs_task: returned %d incidents", len(incidents))
        return incidents
    except Exception as e:
        logger.exception("analyze_logs_task failed: %s", e)
        return []
