"""Limite de tentativas de login, mantido em memoria."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable


class LoginRateLimiter:
    """Janela deslizante de falhas de login, em memoria (instancia unica)."""

    def __init__(
        self,
        max_failures: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}

    def is_blocked(self, key: str) -> bool:
        """Informa se a chave atingiu o limite; descarta falhas fora da janela."""

        failures = self._failures.get(key)
        if failures is None:
            return False

        oldest_allowed = self._clock() - self.window_seconds
        while failures and failures[0] <= oldest_allowed:
            failures.popleft()

        if not failures:
            del self._failures[key]
            return False

        return len(failures) >= self.max_failures

    def register_failure(self, key: str) -> None:
        """Registra uma tentativa de login que falhou."""

        self._failures.setdefault(key, deque()).append(self._clock())

    def reset(self, key: str) -> None:
        """Zera as falhas da chave (login bem-sucedido)."""

        self._failures.pop(key, None)

    def clear(self) -> None:
        """Zera todas as chaves (usado pelos testes)."""

        self._failures.clear()
