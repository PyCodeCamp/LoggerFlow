#!/usr/bin/env python
from __future__ import annotations

import os
import sys
import json
import logging
import traceback
import warnings
from datetime import datetime
from dotenv import load_dotenv
from logger_flow.crew import LoggerFlow

# Initialize environment
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configure logging: [time] [level] [module] message
LOG_FMT = "[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def main():
    """Run the LoggerFlow pipeline end-to-end and print a concise summary."""
    try:
        logger.info("Starting LoggerFlow pipeline")
        crew = LoggerFlow()
        result = crew.run_pipeline()

        # Print short summary
        summary = {
            "logs_scanned": result.get("logs_scanned", 0),
            "incidents_detected": result.get("incidents_detected", 0),
            "jira_tickets_created": result.get("jira_tickets_created", 0),
        }

        print(json.dumps(summary, indent=2))
        logger.info("Pipeline finished: %s", summary)

        # Optionally dump detailed result to a file for inspection
        try:
            out_path = os.path.join(os.getcwd(), "logger_flow_pipeline_result.json")
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
            logger.info("Detailed pipeline result written to %s", out_path)
        except Exception:
            logger.exception("Failed to write detailed pipeline result: %s", traceback.format_exc())

        return result

    except Exception as e:
        logger.exception("LoggerFlow main execution failed: %s", e)
        return {"error": str(e)}


def run():
    """
    Run the crew.
    """
    inputs = {
        'topic': 'AI LLMs',
        'current_year': str(datetime.now().year)
    }

    try:
        LoggerFlow().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        LoggerFlow().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        LoggerFlow().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }

    try:
        LoggerFlow().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",
        "current_year": ""
    }

    try:
        result = LoggerFlow().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")


if __name__ == "__main__":
    main()
