"""
Choices on a dish: "Spice level" (pick one), "Extras" (pick any), "Drink" ...

Stored on the menu item as JSON (`MenuItem.options`):

    [{"id": "g1a2b3c4", "name": "Spice level", "min_select": 1, "max_select": 1,
      "choices": [{"id": "c5d6e7f8", "name": "Hot", "price": "0.00", "available": true}, ...]}]

The customer sends only the ids of the choices they picked. Everything about
money is worked out here from the menu, never taken from the browser.
"""
import secrets
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import HTTPException

from app.schemas.menu import MAX_CHOICES, MAX_GROUPS  # noqa: E402,F401


def _new_id(prefix: str) -> str:
    return prefix + secrets.token_hex(4)


def normalise(groups: Optional[list]) -> list:
    """Validated option groups (from the schema) -> JSON to store, with stable ids."""
    stored = []
    seen = set()
    for group in groups or []:
        group = group if isinstance(group, dict) else group.model_dump()
        group_id = group.get("id") or _new_id("g")
        while group_id in seen:
            group_id = _new_id("g")
        seen.add(group_id)
        choices = []
        for choice in group["choices"]:
            choice_id = choice.get("id") or _new_id("c")
            while choice_id in seen:
                choice_id = _new_id("c")
            seen.add(choice_id)
            choices.append({
                "id": choice_id,
                "name": choice["name"].strip(),
                "price": f"{Decimal(str(choice.get('price') or 0)):.2f}",
                "available": choice.get("available", True) is not False,
            })
        stored.append({
            "id": group_id,
            "name": group["name"].strip(),
            "min_select": int(group["min_select"]),
            "max_select": int(group["max_select"]),
            "choices": choices,
        })
    return stored


def choose(item, choice_ids: List[str]) -> Tuple[Decimal, list]:
    """
    Check what the customer picked for one dish and price it.
    Returns (unit price including extras, snapshot of the picks to keep on the order).
    """
    groups = item.options or []
    wanted = list(dict.fromkeys(choice_ids or []))  # each choice once, in the order picked
    by_id = {choice["id"]: (group, choice) for group in groups for choice in group["choices"]}

    unknown = [cid for cid in wanted if cid not in by_id]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"The choices for {item.name} have changed. Please remove it from your cart and add it again.",
        )

    picked: List[dict] = []
    extra = Decimal("0")
    for group in groups:
        mine = [by_id[cid][1] for cid in wanted if by_id[cid][0]["id"] == group["id"]]
        if len(mine) < group["min_select"]:
            raise HTTPException(status_code=400, detail=f"Please choose {group['name'].lower()} for {item.name}.")
        if len(mine) > group["max_select"]:
            many = "one" if group["max_select"] == 1 else f"up to {group['max_select']}"
            raise HTTPException(status_code=400, detail=f"Choose {many} for {group['name'].lower()} on {item.name}.")
        for choice in mine:
            if not choice.get("available", True):
                raise HTTPException(status_code=400, detail=f"{choice['name']} is not available right now ({item.name}).")
            price = Decimal(str(choice.get("price") or "0"))
            extra += price
            picked.append({"group": group["name"], "name": choice["name"], "price": f"{price:.2f}"})

    return (Decimal(str(item.price)) + extra).quantize(Decimal("0.01")), picked


def describe(picked: Optional[list]) -> str:
    """'Hot, Extra chips' for invoices, SMS and the kitchen."""
    return ", ".join(choice["name"] for choice in (picked or []))
