from __future__ import annotations

import logging
import traceback
from typing import List
from dataclasses import asdict

from ..tools import LogReaderTool, GeminiAnalysisTool, JiraTool, LogEntry

logger = logging.getLogger(__name__)


class LogIngestionAgent:
    def __init__(self, log_dir: str | None = None) -> None:
        self.reader = LogReaderTool(log_dir or "logs")

    def run(self) -> List[LogEntry]:
        try:
            entries = self.reader.read_logs()
            logger.info("LogIngestionAgent: read %d entries", len(entries))
            return entries
        except Exception as e:
            logger.exception("LogIngestionAgent failed: %s", e)
            return []


class LogAnalysisAgent:
    def __init__(self) -> None:
        self.analyzer = GeminiAnalysisTool()

    def run(self, entries: List[LogEntry]) -> List[dict]:
        try:
            serial = [
                {
                    "timestamp": (e.timestamp.isoformat() if e.timestamp else None),
                    "level": e.level,
                    "service": e.service,
                    "message": e.message,
                    "raw": e.raw,
                }
                for e in entries
            ]
            out = self.analyzer._run(serial)
            import json

            parsed = json.loads(out) if out else {"incidents": []}
            incidents = parsed.get("incidents", []) if isinstance(parsed, dict) else []
            logger.info("LogAnalysisAgent: detected %d incidents", len(incidents))
            return incidents
        except Exception as e:
            logger.exception("LogAnalysisAgent failed: %s", e)
            return []


class TicketCreationAgent:
    def __init__(self) -> None:
        self.jira = JiraTool()

    def run(self, incidents: List[dict]) -> List[dict]:
        created = []
        for inc in incidents:
            try:
                title = inc.get("title") or f"Incident in {inc.get('service','unknown')}"
                desc = inc.get("description") or "No description provided"
                svc = inc.get("service")
                url = self.jira._run(title=title, description=desc, service=svc)
                if url:
                    created.append({"title": title, "url": url})
            except Exception as e:
                logger.exception("TicketCreationAgent failed for incident %s: %s", inc, e)
                continue
        logger.info("TicketCreationAgent: created %d tickets", len(created))
        return created
