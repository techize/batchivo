#!/usr/bin/env python3
"""
Quick script to reset a user's password directly in the database.
Usage: python reset_password.py <email> <new_password>
"""

import sys
import asyncio
import bcrypt
from sqlalchemy import select
from app.database import async_session_maker
from app.models.user import User


async def reset_password(email: str, new_password: str):
    """Reset a user's password."""
    async with async_session_maker() as db:
        # Find user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User not found: {email}")
            return False

        # Hash new password
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), salt)
        user.hashed_password = hashed.decode("utf-8")

        await db.commit()
        print(f"✅ Password reset successful for: {email}")
        return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(1)

    email = sys.argv[1]
    new_password = sys.argv[2]

    if len(new_password) < 8:
        print("❌ Password must be at least 8 characters")
        sys.exit(1)

    asyncio.run(reset_password(email, new_password))
