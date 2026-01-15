from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.logger = logging.getLogger(f"agent.{name}")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the agent.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

    def log_activity(self, message: str):
        """Logs agent activity."""
        self.logger.info(f"[{self.name}] {message}")
