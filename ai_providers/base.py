from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAIProvider(ABC):
    @abstractmethod
    async def process_intent(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process user input and extract intent"""
        pass

    @abstractmethod
    async def generate_response(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate natural language response"""
        pass

    @abstractmethod
    async def validate_task_feasibility(
        self, task_type: str, details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if a task can be performed"""
        pass
