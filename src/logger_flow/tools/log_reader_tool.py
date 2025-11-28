from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, ClassVar, Type
import logging

from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    timestamp: datetime | None
    level: str
    service: str
    message: str
    raw: str


class LogReaderInput(BaseModel):
    log_dir: Optional[str] = Field(
        None,
        description="Directory to read logs from. If not provided, uses LOG_DIR env var or default 'logs'.",
    )


class LogReaderTool(BaseTool):
    """Reads .log files from a given directory and parses lines into LogEntry objects.

    This tool is a crewAI BaseTool so it can be passed directly to an Agent.
    """

    # These MUST be normal fields (not ClassVar), because BaseTool / Pydantic
    # will introspect and sometimes mutate them.
    name: str = "log_reader"
    description: str = "Reads .log files from a directory and returns parsed log lines"

    # IMPORTANT: args_schema must be a real Pydantic field, not a ClassVar
    args_schema: Type[BaseModel] = LogReaderInput

    # Regex for lines like:
    # [2025-11-26T12:00:01Z] [INFO] [web] Started request id=...
    LINE_REGEX: ClassVar[re.Pattern] = re.compile(
        r"\[(?P<timestamp>[^\]]+)\]\s+\[(?P<level>INFO|WARN|ERROR|WARNING|DEBUG)\]\s+\[(?P<service>[^\]]+)\]\s+(?P<message>.+)"
    )

    DEFAULT_LOG_DIR: ClassVar[str] = "logs"

    # -----------------------------
    # Core logic used by the tool
    # -----------------------------
    def read_logs(self, log_dir: Optional[str] = None) -> List[LogEntry]:
        """Read logs from provided directory (or LOG_DIR env or default)."""
        entries: List[LogEntry] = []

        dir_to_use = log_dir or os.getenv("LOG_DIR") or self.DEFAULT_LOG_DIR

        if not os.path.isdir(dir_to_use):
            logger.warning("Log directory %s does not exist", dir_to_use)
            return entries

        for root, _, files in os.walk(dir_to_use):
            for fname in sorted(files):
                if not fname.lower().endswith(".log"):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        for raw_line in fh:
                            line = raw_line.strip()
                            if not line:
                                continue
                            parsed = self._parse_line(line)
                            entries.append(parsed)
                except Exception as e:
                    logger.exception("Failed to read log file %s: %s", path, e)
                    continue

        return entries

    def _parse_line(self, line: str) -> LogEntry:
        try:
            m = self.LINE_REGEX.match(line)
            if m:
                ts_raw = m.group("timestamp")
                try:
                    # Handle timestamps like 2025-11-26T12:00:01Z
                    ts = datetime.fromisoformat(ts_raw.replace("Z", ""))
                except Exception:
                    ts = None
                level = m.group("level")
                service = m.group("service") or "unknown"
                message = m.group("message").strip()
                return LogEntry(
                    timestamp=ts,
                    level=level,
                    service=service,
                    message=message,
                    raw=line,
                )

            # fallback: keep the line but mark unknown
            return LogEntry(
                timestamp=None,
                level="UNKNOWN",
                service="unknown",
                message=line,
                raw=line,
            )
        except Exception as e:
            logger.exception("Unexpected error parsing log line: %s", e)
            return LogEntry(
                timestamp=None,
                level="UNKNOWN",
                service="unknown",
                message=line,
                raw=line,
            )

    # -----------------------------
    # REQUIRED BY BaseTool
    # -----------------------------
    def _run(self, log_dir: Optional[str] = None, **kwargs) -> str:
        """Entry point used by CrewAI when the tool is called from an Agent/Task.

        Returns a text dump of parsed log lines, which the LLM can then analyze.
        """
        entries = self.read_logs(log_dir)

        dir_used = log_dir or os.getenv("LOG_DIR") or self.DEFAULT_LOG_DIR

        if not entries:
            return f"No log entries found in directory: {dir_used}"

        lines: List[str] = []
        for e in entries:
            ts = e.timestamp.isoformat() if e.timestamp else "NO_TIMESTAMP"
            lines.append(f"[{ts}] [{e.level}] [{e.service}] {e.message}")

        header = (
            f"Read {len(entries)} log entries from '{dir_used}'. "
            f"Below are the parsed lines (one per line):\n"
        )
        return header + "\n".join(lines)
