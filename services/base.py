from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTaskService(ABC):
    @abstractmethod
    async def execute(
        self, details: Dict[str, Any], user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the task"""
        pass

    @abstractmethod
    async def validate_input(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input parameters"""
        pass
