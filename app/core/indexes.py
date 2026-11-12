"""Indices do MongoDB criados na subida da aplicacao."""

from __future__ import annotations

from typing import Any


async def ensure_indexes(database: Any) -> None:
    """Cria, de forma idempotente, os indices de que o dominio depende."""

    users = database["users"]
    await users.create_index("email", unique=True, name="users_email_unique")
    await users.create_index(
        "username",
        unique=True,
        name="users_username_unique",
        partialFilterExpression={"username": {"$type": "string"}},
    )

    await database["points"].create_index("slug", unique=True, name="points_slug_unique")

    visits = database["visits"]
    await visits.create_index("point_slug", name="visits_point_slug")
    await visits.create_index("visited_at", name="visits_visited_at")
