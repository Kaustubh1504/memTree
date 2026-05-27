"""Typed `submit()` — final answer validated against a Pydantic schema.

The MemEx paper makes the agent's final return value a typed object. In smolagents,
the agent finishes by calling `final_answer(...)`; we subclass that tool so the
payload is coerced/validated through a Pydantic model. Schema violations raise.
"""
from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel, ValidationError
from smolagents.default_tools import FinalAnswerTool


class TypedFinalAnswerError(ValueError):
    """Raised when the agent's final answer doesn't satisfy the declared schema."""


class TypedFinalAnswerTool(FinalAnswerTool):
    """Drop-in replacement for `FinalAnswerTool` that validates against a Pydantic model.

    The agent can pass either a dict matching the schema or an already-built instance.
    """

    def __init__(self, schema: Type[BaseModel]):
        super().__init__()
        self.schema = schema
        self.description = (
            f"Provides the final answer. The answer must match the {schema.__name__} "
            f"schema with fields: {list(schema.model_fields.keys())}. "
            "Pass it either as a dict matching that shape or as an instance of the model."
        )
        # Surface the schema in the tool's input type so the LLM sees the contract.
        self.inputs = {
            "answer": {
                "type": "object",
                "description": f"A {schema.__name__} object or dict matching its schema.",
            }
        }

    def forward(self, answer: Any) -> BaseModel:
        if isinstance(answer, self.schema):
            return answer
        try:
            if isinstance(answer, BaseModel):
                return self.schema.model_validate(answer.model_dump())
            if isinstance(answer, dict):
                return self.schema.model_validate(answer)
            return self.schema.model_validate(answer)
        except ValidationError as e:
            raise TypedFinalAnswerError(
                f"Final answer does not match {self.schema.__name__}: {e}"
            ) from e
