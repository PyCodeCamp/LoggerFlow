from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import logging
import traceback

from .tools import LogReaderTool, GeminiAnalysisTool, JiraTool

logger = logging.getLogger(__name__)


@CrewBase
class LoggerFlow():
    """LoggerFlow crew: defines agents and a simple pipeline runner.

    The class exposes run_pipeline(inputs) which performs:
    - Log ingestion via LogReaderTool
    - Analysis via GeminiAnalysisTool
    - Jira ticket creation via JiraTool

    This keeps behaviour robust with extensive error handling and logging.
    """

    agents: List[BaseAgent]
    tasks: List[Task]

    # Provide YAML config paths (keeps compatibility with CrewBase expectations)
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def log_ingestor(self) -> Agent:
        # Agent config in agents.yaml under 'log_ingestor'
        return Agent(
            config=self.agents_config['log_ingestor'],  # type: ignore[index]
            verbose=True,
            tools=[LogReaderTool()],
        )

    @agent
    def log_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['log_analyzer'],  # type: ignore[index]
            verbose=True,
            tools=[GeminiAnalysisTool()],
        )

    @agent
    def ticket_creator(self) -> Agent:
        return Agent(
            config=self.agents_config['ticket_creator'],  # type: ignore[index]
            verbose=True,
            tools=[JiraTool()],
        )

    @task
    def ingest_logs_task(self) -> Task:
        return Task(
            config=self.tasks_config['ingest_logs_task'],  # type: ignore[index]
        )

    @task
    def analyze_logs_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_logs_task'],  # type: ignore[index]
        )

    @task
    def create_tickets_task(self) -> Task:
        return Task(
            config=self.tasks_config['create_tickets_task'],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the LoggerFlow crew (sequential pipeline)."""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )

    def run_pipeline(self, inputs: dict | None = None) -> dict:
        """Execute the end-to-end pipeline using local tools.

        This method is deliberately resilient: it never raises; it logs exceptions
        and returns a summary dict with counts and lists of incidents/tickets.
        """
        summary = {
            "logs_scanned": 0,
            "incidents_detected": 0,
            "jira_tickets_created": 0,
            "incidents": [],
            "tickets": [],
            "errors": [],
        }

        try:
            # 1) Ingest logs
            reader = LogReaderTool()
            entries = []
            try:
                entries = reader.read_logs()
                summary["logs_scanned"] = len(entries)
                logger.info("Ingested %d log entries", len(entries))
            except Exception as e:
                logger.exception("Error ingesting logs: %s", e)
                summary["errors"].append({"stage": "ingest", "error": str(e), "trace": traceback.format_exc()})

            # Prepare serialized logs for Gemini
            serial_logs = [
                {
                    "timestamp": (le.timestamp.isoformat() if le.timestamp else None),
                    "level": le.level,
                    "service": le.service,
                    "message": le.message,
                    "raw": le.raw,
                }
                for le in entries
            ]

            # 2) Analyze logs via Gemini
            analyzer = GeminiAnalysisTool()
            incidents = []
            try:
                gemini_out = analyzer._run(serial_logs)
                # gemini_out is JSON string with {"incidents": [...]}
                import json

                parsed = json.loads(gemini_out)
                incidents = parsed.get("incidents", []) if isinstance(parsed, dict) else []
                summary["incidents_detected"] = len(incidents)
                summary["incidents"] = incidents
                logger.info("Gemini detected %d incidents", len(incidents))
            except Exception as e:
                logger.exception("Error analyzing logs with Gemini: %s", e)
                summary["errors"].append({"stage": "analyze", "error": str(e), "trace": traceback.format_exc()})

            # 3) Create Jira tickets for each incident
            jira = JiraTool()
            tickets = []
            for inc in incidents:
                try:
                    title = inc.get("title") or f"Incident in {inc.get('service','unknown')}"
                    desc = inc.get("description") or "No description provided"
                    service = inc.get("service")
                    issue_url = jira._run(title=title, description=desc, service=service)
                    if issue_url:
                        tickets.append({"incident": title, "url": issue_url})
                        summary["jira_tickets_created"] += 1
                        logger.info("Created Jira ticket for incident: %s -> %s", title, issue_url)
                    else:
                        logger.error("Failed to create Jira ticket for incident: %s", title)
                except Exception as e:
                    logger.exception("Error creating ticket for incident %s: %s", inc, e)
                    summary["errors"].append({"stage": "ticket", "incident": inc, "error": str(e), "trace": traceback.format_exc()})

            summary["tickets"] = tickets

        except Exception as e:
            logger.exception("Unexpected pipeline error: %s", e)
            summary["errors"].append({"stage": "pipeline", "error": str(e), "trace": traceback.format_exc()})

        return summary
