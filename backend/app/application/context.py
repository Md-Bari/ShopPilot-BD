from dataclasses import dataclass

from app.domain.enums import Role
from app.domain.errors import PermissionDeniedError


@dataclass(frozen=True)
class TenantContext:
    """Who is acting, and on behalf of which business. Built only by the API layer after
    verifying the user's membership, so services can trust `business_id`."""

    user_id: int
    business_id: int
    role: Role

    def require(self, *roles: Role) -> None:
        if self.role not in roles:
            raise PermissionDeniedError("You do not have permission to perform this action.")
