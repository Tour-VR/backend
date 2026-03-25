from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import MongoManager
from main import app


def test_import_main_works() -> None:
    imported_app = app
    assert imported_app is not None


def test_root_route_returns_basic_metadata() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Bem-vindo ao backend MVP",
        "docs": "/docs",
        "health": "/health/",
    }


def test_auth_login_preflight_allows_frontend_origin(monkeypatch) -> None:
    async def fake_ping(self: MongoManager) -> bool:
        self.connected = True
        self.last_error = None
        return True

    monkeypatch.setattr(
        MongoManager,
        "_has_placeholder_credentials",
        lambda self: False,
    )
    monkeypatch.setattr(MongoManager, "ping", fake_ping)

    with TestClient(app) as client:
        response = client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_health_route_reports_database_down(monkeypatch) -> None:
    async def fake_ping(self: MongoManager) -> bool:
        self.connected = False
        self.last_error = "MongoDB indisponivel para teste."
        return False

    monkeypatch.setattr(
        MongoManager,
        "_has_placeholder_credentials",
        lambda self: False,
    )
    monkeypatch.setattr(MongoManager, "ping", fake_ping)

    with TestClient(app) as client:
        response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "api": {"status": "ok"},
        "database": {
            "status": "down",
            "connected": False,
            "database": settings.mongodb_db,
            "detail": "MongoDB indisponivel para teste.",
        },
    }


def test_health_route_reports_database_up(monkeypatch) -> None:
    async def fake_ping(self: MongoManager) -> bool:
        self.connected = True
        self.last_error = None
        return True

    monkeypatch.setattr(
        MongoManager,
        "_has_placeholder_credentials",
        lambda self: False,
    )
    monkeypatch.setattr(MongoManager, "ping", fake_ping)

    with TestClient(app) as client:
        response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api": {"status": "ok"},
        "database": {
            "status": "up",
            "connected": True,
            "database": settings.mongodb_db,
            "detail": "MongoDB conectado com sucesso.",
        },
    }


def test_connect_reports_placeholder_password_without_network() -> None:
    import asyncio

    manager = MongoManager(
        "mongodb+srv://usuario:<db_password>@cluster.mongodb.net/",
        settings.mongodb_db,
    )

    asyncio.run(manager.connect())

    assert manager.connected is False
    assert manager.last_error == (
        "A URL do MongoDB ainda contem um placeholder de senha. "
        "Substitua `<db_password>` pela senha real do usuario Atlas."
    )
