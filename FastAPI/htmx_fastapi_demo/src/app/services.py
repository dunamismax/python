# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# filename: services.py
# author: dunamismax
# version: 1.0.0
# date: 06-17-2025
# github: https://github.com/dunamismax
# description: In-memory data service layer for the application.
# -----------------------------------------------------------------------------
from typing import Self

from src.app.schemas import Item, ItemCreate


class ItemRepository:
    """
    An in-memory repository for managing items.

    Note: In a production system, this would be replaced with an
    asynchronous database repository (e.g., using asyncpg) that
    implements the same interface.
    """

    def __init__(self: Self) -> None:
        """Initializes the repository with an empty item list."""
        self._items: list[Item] = []

    async def get_all(self: Self) -> list[Item]:
        """
        Asynchronously retrieves all items, sorted by creation time.

        Returns:
            A list of all Item objects.
        """
        return sorted(self._items, key=lambda item: item.created_at, reverse=True)

    async def create(self: Self, item_data: ItemCreate) -> Item:
        """
        Asynchronously creates a new item and adds it to the repository.

        Args:
            item_data: The validated data for the new item.

        Returns:
            The newly created Item object.
        """
        new_item = Item(name=item_data.name)
        self._items.append(new_item)
        return new_item


# Singleton instance of the repository
# This simulates a persistent data store for the application's lifecycle.
item_repo = ItemRepository()
