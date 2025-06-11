"""Run database migrations."""

import asyncio
import asyncpg
import os
from pathlib import Path
import structlog

logger = structlog.get_logger()


async def run_migrations():
    """Run all database migrations."""
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/url_to_llm")
    
    logger.info("Connecting to database", url=database_url)
    conn = await asyncpg.connect(database_url)
    
    try:
        # Create migrations table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        
        # Get list of applied migrations
        applied = await conn.fetch("SELECT filename FROM migrations")
        applied_files = {row['filename'] for row in applied}
        
        # Get migration files
        migrations_dir = Path(__file__).parent / "app" / "db" / "migrations"
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        for migration_file in migration_files:
            filename = migration_file.name
            
            if filename in applied_files:
                logger.info("Skipping migration (already applied)", filename=filename)
                continue
                
            logger.info("Applying migration", filename=filename)
            
            # Read and execute migration
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
                
            try:
                # Execute in transaction
                async with conn.transaction():
                    await conn.execute(migration_sql)
                    await conn.execute(
                        "INSERT INTO migrations (filename) VALUES ($1)",
                        filename
                    )
                logger.info("Migration applied successfully", filename=filename)
                
            except Exception as e:
                logger.error("Migration failed", filename=filename, error=str(e))
                raise
                
    finally:
        await conn.close()
        
    logger.info("All migrations completed")


if __name__ == "__main__":
    asyncio.run(run_migrations())