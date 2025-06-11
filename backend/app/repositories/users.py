"""User repository for database operations."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import asyncpg
import structlog

from ..models.auth import User

logger = structlog.get_logger()


class UserRepository:
    """Repository for user-related database operations."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def create_user(
        self,
        email: str,
        username: str,
        hashed_password: str,
        is_superuser: bool = False
    ) -> User:
        """Create a new user in the database."""
        query = """
            INSERT INTO users (id, email, username, hashed_password, is_superuser)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """
        
        user_id = uuid4()
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                user_id,
                email,
                username,
                hashed_password,
                is_superuser
            )
            
            return User(
                id=row['id'],
                email=row['email'],
                username=row['username'],
                hashed_password=row['hashed_password'],
                is_active=row['is_active'],
                is_superuser=row['is_superuser'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE id = $1"
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            if not row:
                return None
            
            return User(
                id=row['id'],
                email=row['email'],
                username=row['username'],
                hashed_password=row['hashed_password'],
                is_active=row['is_active'],
                is_superuser=row['is_superuser'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = "SELECT * FROM users WHERE email = $1"
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, email)
            
            if not row:
                return None
            
            return User(
                id=row['id'],
                email=row['email'],
                username=row['username'],
                hashed_password=row['hashed_password'],
                is_active=row['is_active'],
                is_superuser=row['is_superuser'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        query = "SELECT * FROM users WHERE username = $1"
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, username)
            
            if not row:
                return None
            
            return User(
                id=row['id'],
                email=row['email'],
                username=row['username'],
                hashed_password=row['hashed_password'],
                is_active=row['is_active'],
                is_superuser=row['is_superuser'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def update_user(
        self,
        user_id: UUID,
        email: Optional[str] = None,
        username: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> User:
        """Update user information."""
        updates = []
        values = [user_id]
        param_count = 1
        
        if email is not None:
            param_count += 1
            updates.append(f"email = ${param_count}")
            values.append(email)
        
        if username is not None:
            param_count += 1
            updates.append(f"username = ${param_count}")
            values.append(username)
        
        if is_active is not None:
            param_count += 1
            updates.append(f"is_active = ${param_count}")
            values.append(is_active)
        
        if not updates:
            return await self.get_user(user_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING *
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            
            return User(
                id=row['id'],
                email=row['email'],
                username=row['username'],
                hashed_password=row['hashed_password'],
                is_active=row['is_active'],
                is_superuser=row['is_superuser'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def update_password(self, user_id: UUID, hashed_password: str) -> None:
        """Update user's password."""
        query = """
            UPDATE users
            SET hashed_password = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, user_id, hashed_password)
    
    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        query = """
            UPDATE users
            SET last_login_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, user_id)
    
    async def delete_user(self, user_id: UUID) -> None:
        """Delete a user (soft delete by deactivating)."""
        query = """
            UPDATE users
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, user_id)
    
    async def verify_user_credentials(self, username: str, password_hash: str) -> Optional[User]:
        """Verify user credentials for login."""
        query = """
            SELECT * FROM users
            WHERE (email = $1 OR username = $1)
            AND hashed_password = $2
            AND is_active = true
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, username, password_hash)
            
            if not row:
                return None
            
            # Update last login
            await self.update_last_login(row['id'])
            
            return User(
                id=row['id'],
                email=row['email'],
                username=row['username'],
                hashed_password=row['hashed_password'],
                is_active=row['is_active'],
                is_superuser=row['is_superuser'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )