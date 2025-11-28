from __future__ import annotations

import os
import time
import logging
from typing import Optional, ClassVar, Type

from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import httpx

logger = logging.getLogger(__name__)


class JiraIssueInput(BaseModel):
    title: str = Field(..., description="Short summary of the issue")
    description: str = Field(..., description="Detailed description of the issue")
    service: Optional[str] = Field(
        None,
        description="Service or component related to this issue (used as a label)",
    )
    project_key: Optional[str] = Field(
        None,
        description="Jira project key; if not provided, uses JIRA_PROJECT_KEY from env",
    )


class JiraTool(BaseTool):
    # Pydantic / BaseTool fields
    name: str = "jira_tool"
    description: str = "Create Jira Cloud issues using the Jira REST API"
    args_schema: Type[BaseModel] = JiraIssueInput

    # Environment-driven configuration
    BASE_URL: ClassVar[Optional[str]] = os.getenv("JIRA_BASE_URL")
    EMAIL: ClassVar[Optional[str]] = os.getenv("JIRA_EMAIL")
    API_TOKEN: ClassVar[Optional[str]] = os.getenv("JIRA_API_TOKEN")
    # From your URL https://pycodecamp.atlassian.net/browse/SCRUM-2
    # the project key is very likely "SCRUM"
    DEFAULT_PROJECT: ClassVar[Optional[str]] = os.getenv("JIRA_PROJECT_KEY", "SCRUM")
    ISSUE_TYPE: ClassVar[str] = os.getenv("JIRA_ISSUE_TYPE", "Task")

    TIMEOUT: ClassVar[int] = 15
    MAX_RETRIES: ClassVar[int] = 3
    RETRY_BACKOFF: ClassVar[int] = 2

    def _run(
        self,
        title: str,
        description: str,
        service: Optional[str] = None,
        project_key: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Create a Jira issue and return its URL (or empty string on failure)."""
        project = project_key or self.DEFAULT_PROJECT
        if not (self.BASE_URL and self.EMAIL and self.API_TOKEN and project):
            logger.error("Jira credentials or project key not set; cannot create issue")
            return ""

        url = self.BASE_URL.rstrip("/") + "/rest/api/3/issue"
        auth = (self.EMAIL, self.API_TOKEN)

        # --- IMPORTANT CHANGE: description as Atlassian Document Format (ADF) ---
        adf_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": description},
                    ],
                }
            ],
        }

        fields: dict = {
            "project": {"key": project},
            "summary": title[:254],  # safety for summary length
            "description": adf_description,
            "issuetype": {"name": self.ISSUE_TYPE},
        }

        if service:
            fields.setdefault("labels", []).append(service)

        payload = {"fields": fields}

        attempt = 0
        while attempt < self.MAX_RETRIES:
            try:
                with httpx.Client(timeout=self.TIMEOUT) as client:
                    resp = client.post(
                        url,
                        json=payload,
                        auth=auth,
                        headers={"Accept": "application/json"},
                    )
                    try:
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as e:
                        # Log Jira's error details before deciding what to do
                        error_body = None
                        try:
                            error_body = resp.json()
                        except Exception:
                            error_body = resp.text

                        logger.error(
                            "Jira API returned HTTP error (%s): %s\nResponse body: %s",
                            resp.status_code,
                            e,
                            error_body,
                        )

                        # For server errors, we can retry; for 5xx we retry, for 4xx we stop
                        if 500 <= resp.status_code < 600:
                            attempt += 1
                            time.sleep(self.RETRY_BACKOFF**attempt)
                            continue
                        return ""

                    data = resp.json()
                    issue_key = data.get("key")
                    issue_url = (
                        f"{self.BASE_URL.rstrip('/')}/browse/{issue_key}"
                        if issue_key
                        else ""
                    )
                    logger.info("Created Jira issue %s", issue_key)
                    return issue_url or issue_key or ""
            except Exception as e:
                logger.exception("Network error when creating Jira issue: %s", e)
                attempt += 1
                time.sleep(self.RETRY_BACKOFF**attempt)
                continue

        logger.error("Failed to create Jira issue after %s attempts", self.MAX_RETRIES)
        return ""
