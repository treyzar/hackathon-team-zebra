"""CLI to assign a role, e.g. to bootstrap the first admin.

Usage (from backend/src): python set_role.py <username> <student|curator|admin>
"""

import asyncio
import sys

from sqlalchemy import select

from database import async_factory, dbengine
from models import Role, User


async def main(username: str, role: Role) -> None:
    async with async_factory() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if not user:
            sys.exit(f"User {username!r} not found")
        user.role = role
        await db.commit()
    await dbengine.dispose()
    print(f"{username} is now {role.value}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in {r.value for r in Role}:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1], Role(sys.argv[2])))
