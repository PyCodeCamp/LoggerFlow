from __future__ import annotations

import os
import json
import logging
from typing import List, Any, ClassVar, Type

from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from crewai import LLM

logger = logging.getLogger(__name__)


class GeminiAnalysisInput(BaseModel):
    logs: List[dict] = Field(
        ...,
        description="List of log entries as dicts",
    )


class GeminiAnalysisTool(BaseTool):
    # IMPORTANT: these must be normal fields (not ClassVar)
    name: str = "gemini_analysis"
    description: str = (
        "Analyze logs using Google Gemini and return structured incidents as JSON"
    )
    args_schema: Type[BaseModel] = GeminiAnalysisInput

    # Config via env (CrewAI Gemini integration)
    GEMINI_MODEL: ClassVar[str] = os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash")
    GEMINI_KEY: ClassVar[str | None] = (
        os.getenv("GEMINI_API_KEY")
    )
    TIMEOUT: ClassVar[int] = 30

    def _run(self, logs: List[dict], **kwargs) -> str:
        """Analyze logs with Gemini and return JSON string: {"incidents": [...]}."""
        if not self.GEMINI_KEY:
            logger.error(
                "GEMINI_API_KEY or GOOGLE_API_KEY not set; skipping Gemini analysis"
            )
            return json.dumps({"incidents": []})

        # Build prompt from logs
        prompt = self._build_prompt(logs)

        # Create LLM instance using CrewAI's native Gemini integration
        # (model and temperature as you requested)
        llm = LLM(
            model=self.GEMINI_MODEL,
            api_key=self.GEMINI_KEY,
            temperature=0.7,
            timeout=self.TIMEOUT,
        )

        try:
            # Call the model; CrewAI's LLM interface uses .call(prompt) for text
            text = llm.call(prompt)

            # Parse JSON array of incidents from model output
            incidents = self._extract_json_from_text(text)
            if incidents is None:
                logger.error("Gemini returned non-JSON or invalid output; skipping")
                return json.dumps({"incidents": []})

            return json.dumps({"incidents": incidents})

        except Exception as e:
            logger.exception("Gemini analysis failed: %s", e)
            return json.dumps({"incidents": []})

    # ----------------- Internal helpers -----------------

    def _build_prompt(self, logs: List[dict]) -> str:
        # Keep prompt concise; ask for strict JSON array of incidents
        sample_limit = 200
        summary_lines = []
        for log in logs[:sample_limit]:
            ts = log.get("timestamp")
            lvl = log.get("level")
            svc = log.get("service")
            msg = log.get("message")
            summary_lines.append(f"{ts} | {lvl} | {svc} | {msg}")

        logs_text = "\n".join(summary_lines)

        instructions = (
            "You are an observability assistant. Analyze the following logs and return "
            "a strict JSON array of incidents.\n\n"
            "Each incident MUST be an object with exactly these keys:\n"
            '- "title": short human-readable title\n'
            '- "description": detailed explanation\n'
            '- "service": service/component name (string)\n'
            '- "severity": one of [\"LOW\", \"MEDIUM\", \"HIGH\", \"CRITICAL\"]\n'
            '- "occurrences": integer count of how many times this pattern appears\n\n'
            "Group repeated error patterns into single incidents. "
            "If no incidents are found, return an empty array [].\n\n"
            "Logs:\n"
            f"{logs_text}\n\n"
            "Return ONLY the JSON array. Do not include any extra text or explanation."
        )
        return instructions

    def _extract_json_from_text(self, text: str) -> list[dict] | None:
        text = text.strip()
        if not text:
            return None

        # Fast path: model already returned a pure JSON array or object
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and isinstance(parsed.get("incidents"), list):
                return parsed["incidents"]
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fallback: find first JSON array substring
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                logger.exception(
                    "Failed to parse JSON candidate from Gemini output; candidate was: %s",
                    candidate[:500],
                )
                return None

        return None
