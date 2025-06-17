# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# filename: routes.py
# author: dunamismax
# version: 1.1.0
# date: 06-17-2025
# github: https://github.com/dunamismax
# description: FastAPI router for serving HTML and handling HTMX requests.
# -----------------------------------------------------------------------------
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi_htmx import htmx

from src.app.config import settings  # <-- IMPORT ADDED
from src.app.schemas import Item, ItemCreate
from src.app.services import ItemRepository, item_repo

# Configure router and templates
router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/", response_class=HTMLResponse, name="index")
async def get_index(
    request: Request,
    repo: ItemRepository = Depends(lambda: item_repo),
) -> HTMLResponse:
    """
    Serves the main index page.

    Retrieves all current items and renders them in the main template.

    Args:
        request: The incoming request object.
        repo: The item repository dependency.

    Returns:
        An HTML response containing the rendered page.
    """
    items: list[Item] = await repo.get_all()
    # Add settings to the context dictionary
    context = {"request": request, "items": items, "settings": settings}
    return templates.TemplateResponse("index.html", context)


@router.post("/items", response_class=HTMLResponse, name="add_item")
@htmx("item", "oob-swap")
async def add_item(
    request: Request,
    item_name: str = Form(..., alias="itemName"),
    repo: ItemRepository = Depends(lambda: item_repo),
) -> HTMLResponse:
    """
    Handles the creation of a new item via an HTMX POST request.

    Validates the incoming form data, creates a new item, and returns
    an HTML partial of the new item.

    Args:
        request: The incoming request object.
        item_name: The name of the item from the form data.
        repo: The item repository dependency.

    Returns:
        An HTML response containing the rendered partial for the new item.
    """
    item_data = ItemCreate(name=item_name)
    new_item: Item = await repo.create(item_data)
    # The partial does not require the full settings context
    context = {"request": request, "item": new_item}
    return templates.TemplateResponse("partials/item.html", context)
