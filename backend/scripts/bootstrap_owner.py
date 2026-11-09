import getpass
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.user import User


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m scripts.bootstrap_owner "
            "<organisation-uuid>"
        )

    try:
        organisation_id = uuid.UUID(sys.argv[1])
    except ValueError:
        raise SystemExit("Invalid organisation UUID")

    email = input("Owner email: ").strip().lower()

    if not email or len(email) > 320 or "@" not in email:
        raise SystemExit("Invalid email address")

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")

    if password != confirmation:
        raise SystemExit("Passwords do not match")

    if len(password) < 16:
        raise SystemExit("Password must contain at least 16 characters")

    with SessionLocal() as db:
        organisation = db.get(Organisation, organisation_id)

        if organisation is None:
            raise SystemExit("Organisation not found")

        existing_owner = db.scalar(
            select(OrganisationMembership)
            .where(
                OrganisationMembership.organisation_id
                == organisation_id,
                OrganisationMembership.role == "owner",
            )
        )

        if existing_owner is not None:
            raise SystemExit(
                "Organisation already has an owner. "
                "No changes made."
            )

        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user is not None:
            raise SystemExit(
                "Email already belongs to an existing account. "
                "No changes made."
            )

        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )

        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            user_id=user.id,
            organisation_id=organisation_id,
            role="owner",
        )

        db.add(membership)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise SystemExit(
                "Account provisioning conflict. "
                "Transaction rolled back."
            )

        print("Owner account created successfully.")
        print("Organisation:", organisation_id)
        print("Role: owner")


if __name__ == "__main__":
    main()
