# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# filename: schemas.py
# author: dunamismax
# version: 1.1.0
# date: 06-17-2025
# github: https://github.com/dunamismax
# description: Pydantic models for data validation and schema definition.
# -----------------------------------------------------------------------------
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Item(BaseModel):
    """
    Represents a single item in our system.

    This model is immutable to ensure data integrity after creation.
    """

    # Correct Pydantic V2 model configuration.
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ItemCreate(BaseModel):
    """
    Schema for creating a new item. Validates incoming data.
    """

    name: str
