import asyncio
import getpass
import sys

from core.security import hash_password
from crud.user import user_crud
from database.seed import seed_user_groups
from database.session import async_session
from models.user import UserGroupEnum


async def main() -> None:
    email = input("Email: ").strip()
    if not email:
        print("Email is required.")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if not password:
        print("Password is required.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)

    async with async_session() as db:
        await seed_user_groups(db)

        existing = await user_crud.get_by_email(db, email)
        if existing is not None:
            await user_crud.change_group(db, existing, UserGroupEnum.ADMIN)
            if not existing.is_active:
                await user_crud.update(db, existing, is_active=True)
            print(f"Existing user '{email}' promoted to admin.")
        else:
            user = await user_crud.create_user(
                db,
                email=email,
                hashed_password=hash_password(password),
                group_name=UserGroupEnum.ADMIN,
            )
            await user_crud.update(db, user, is_active=True)
            print(f"Admin user '{email}' created successfully.")


if __name__ == "__main__":
    asyncio.run(main())
