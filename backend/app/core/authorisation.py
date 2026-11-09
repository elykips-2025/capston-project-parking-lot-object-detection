import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.organisation_membership import OrganisationMembership
from app.models.user import User


def require_organisation_role(*allowed_roles: str):
    valid_roles = {"owner", "admin", "viewer"}

    if not allowed_roles or not set(allowed_roles) <= valid_roles:
        raise ValueError("Invalid organisation role configuration")

    def dependency(
        organisation_id: uuid.UUID,
        user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> OrganisationMembership:

        membership = db.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id
                == organisation_id,
                OrganisationMembership.user_id == user.id,
            )
        )

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organisation not found",
            )

        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient organisation permissions",
            )

        return membership

    return dependency


RequireOrganisationViewer = Annotated[
    OrganisationMembership,
    Depends(
        require_organisation_role(
            "owner", "admin", "viewer"
        )
    ),
]

RequireOrganisationAdmin = Annotated[
    OrganisationMembership,
    Depends(
        require_organisation_role(
            "owner", "admin"
        )
    ),
]

RequireOrganisationOwner = Annotated[
    OrganisationMembership,
    Depends(
        require_organisation_role("owner")
    ),
]
