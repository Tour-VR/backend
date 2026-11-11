"""Comandos administrativos: python -m app.cli create-admin --email X --password Y."""

from __future__ import annotations

import argparse
import asyncio
import sys

from pydantic import ValidationError

from app.core.config import settings
from app.core.database import MongoManager
from app.core.indexes import ensure_indexes
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.services.user_service import UserInputError, UserService

EXIT_OK = 0
EXIT_DATABASE_UNAVAILABLE = 1
EXIT_INVALID_INPUT = 2


def build_parser() -> argparse.ArgumentParser:
    """Monta o parser com o subcomando create-admin."""

    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subcommands.add_parser(
        "create-admin",
        help="Cria um administrador ou promove um usuario existente.",
    )
    create_admin_parser.add_argument("--email", required=True)
    create_admin_parser.add_argument("--password", required=True)
    create_admin_parser.add_argument("--full-name", default=None)
    return parser


def _format_validation_error(exc: ValidationError) -> str:
    """Lista os erros do Pydantic sem repetir o valor informado (a senha, por exemplo)."""

    messages = []
    for error in exc.errors(include_input=False, include_url=False):
        field = ".".join(str(part) for part in error["loc"])
        messages.append(f"{field}: {error['msg']}")
    return "; ".join(messages)


async def create_admin(email: str, password: str, full_name: str | None) -> int:
    """Cria ou promove o administrador e devolve o codigo de saida do processo."""

    try:
        payload = UserCreate(email=email, password=password, full_name=full_name)
    except ValidationError as exc:
        print(f"Dados invalidos: {_format_validation_error(exc)}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    manager = MongoManager(settings.mongodb_url, settings.mongodb_db)
    try:
        await manager.connect()
        if not manager.connected:
            print(f"Banco de dados indisponivel: {manager.last_error}", file=sys.stderr)
            return EXIT_DATABASE_UNAVAILABLE

        await ensure_indexes(manager.database)
        service = UserService(UserRepository(manager.database))
        try:
            user, created = await service.create_or_promote_admin(payload)
        except ConnectionError as exc:
            print(f"Banco de dados indisponivel: {exc}", file=sys.stderr)
            return EXIT_DATABASE_UNAVAILABLE
        except UserInputError as exc:
            print(f"Dados invalidos: {exc}", file=sys.stderr)
            return EXIT_INVALID_INPUT
    finally:
        await manager.close()

    if created:
        print(f"Administrador criado: {user['email']}")
    else:
        print(f"Usuario promovido a administrador: {user['email']}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada do comando de linha."""

    args = build_parser().parse_args(argv)
    # Hoje so existe create-admin; o subparser obrigatorio garante o valor.
    return asyncio.run(create_admin(args.email, args.password, args.full_name))


if __name__ == "__main__":
    raise SystemExit(main())
