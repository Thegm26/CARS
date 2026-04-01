from __future__ import annotations

from cars_returns.models import User


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class TokenAuth:
    def __init__(self, users_by_token: dict[str, User]) -> None:
        self._users_by_token = users_by_token

    def authenticate(self, authorization_header: str | None) -> User:
        if not authorization_header:
            raise AuthenticationError("missing authorization header")
        prefix = "Bearer "
        if not authorization_header.startswith(prefix):
            raise AuthenticationError("unsupported authorization scheme")
        token = authorization_header[len(prefix) :].strip()
        user = self._users_by_token.get(token)
        if user is None:
            raise AuthenticationError("unknown token")
        return user


def require_role(user: User, allowed_roles: set[str]) -> None:
    if user.role not in allowed_roles:
        raise AuthorizationError(f"role {user.role} is not allowed")

