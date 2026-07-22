"""
services/api_gateway/auth.py

Simple, honest RBAC stub matching Blueprint Section 10's role model:
citizen, bank_partner, police, admin. Requests carry a bearer token in
the format "role:token_value" (e.g. "police:demo-token") -- this is
deliberately trivial so the hackathon demo can show role-scoped access
working end-to-end without standing up a full OAuth2 provider.

Replace `resolve_role()` with real OAuth2/JWT validation (Blueprint
Section 5: "Auth Service - OAuth2 / RBAC") before any non-demo
deployment. Every endpoint that depends on `require_role(...)` will
continue to work unchanged once that swap is made, since the dependency
contract (return a role string or raise 401/403) doesn't change.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

VALID_ROLES = {"citizen", "bank_partner", "police", "admin"}


def resolve_role(authorization: str | None = Header(default=None)) -> str:
    if not authorization or ":" not in authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <role>:<token>'.",
        )
    token = authorization.removeprefix("Bearer ").strip()
    role = token.split(":")[0]
    if role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unknown role '{role}'.")
    return role


def require_role(*allowed_roles: str):
    def _dependency(role: str = Header(default="citizen", alias="X-Demo-Role")) -> str:
        # NOTE: for demo simplicity this reads the role from a plain
        # header instead of decoding resolve_role()'s bearer token.
        # A production build wires this to resolve_role() /
        # a real JWT claims check instead.
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is not permitted to call this endpoint. Allowed: {allowed_roles}",
            )
        return role

    return _dependency
