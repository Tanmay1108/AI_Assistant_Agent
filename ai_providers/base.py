from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel


class BaseAIProvider(ABC):
    @abstractmethod
    async def get_response(
        self, system_prompt: str, user_prompt: str, output_schema: BaseModel
    ) -> Dict[Any, Any]:
        """Generate the response with the given prompts"""
        pass
