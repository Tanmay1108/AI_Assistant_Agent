import json
from typing import Any, Dict, Optional, Type

import openai
from pydantic import BaseModel, ValidationError

from core.config import settings

from .base import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def _check_response_format(
        response, output_schema: Type[BaseModel]
    ) -> BaseModel:
        """
        Validate LLM JSON output against expected schema.
        Assumes API call used JSON-only mode.
        """
        try:
            raw_json = response.choices[0].message.content  # this is not tested.
            parsed = json.loads(raw_json)
        except (AttributeError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid JSON in response: {e}")

        try:
            return output_schema.model_validate(parsed)
        except ValidationError as e:
            raise ValueError(
                f"Response does not match schema {output_schema.__name__}: {e}"
            )

    async def get_response(
        self, system_prompt: str, user_prompt: str, output_schema: BaseModel
    ) -> Dict[Any, Any]:
        try:
            system_prompt = (
                system_prompt
                + f"Provide output in JSON FORMAT as per the schema: {output_schema.model_dump()}"
            )
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]
            response = await self.client.chat.completions.create(
                model=settings.GPT_Model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"},  # JSON-only mode
            )
            await _check_response_format(response, output_schema)
            return json.loads(response)
        except:
            raise
