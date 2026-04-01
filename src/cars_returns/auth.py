from __future__ import annotations

import hashlib
import secrets
from http import cookies

from cars_returns.models import User


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class SessionAuth:
    def __init__(self, repository) -> None:
        self._repository = repository
        self._sessions: dict[str, str] = {}

    def login(self, email: str, password: str) -> tuple[str, User]:
        user = self._repository.get_user_by_email(email)
        if user is None or user.password_hash != hash_password(password):
            raise AuthenticationError("invalid email or password")
        session_id = secrets.token_urlsafe(24)
        self._sessions[session_id] = user.id
        return session_id, user

    def logout(self, session_id: str | None) -> None:
        if session_id:
            self._sessions.pop(session_id, None)

    def authenticate_request(self, cookie_header: str | None) -> User:
        session_id = self.extract_session_id(cookie_header)
        if session_id is None:
            raise AuthenticationError("login required")
        user_id = self._sessions.get(session_id)
        if user_id is None:
            raise AuthenticationError("invalid session")
        user = self._repository.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationError("unknown user")
        return user

    @staticmethod
    def extract_session_id(cookie_header: str | None) -> str | None:
        if not cookie_header:
            return None
        jar = cookies.SimpleCookie()
        jar.load(cookie_header)
        morsel = jar.get("cars_session")
        return morsel.value if morsel else None


def require_role(user: User, allowed_roles: set[str]) -> None:
    if user.role not in allowed_roles:
        raise AuthorizationError(f"role {user.role} is not allowed")
