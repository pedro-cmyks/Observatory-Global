#!/usr/bin/env python3
"""
Database migration runner for Observatory Global.

Usage:
    python -m app.db.migrate              # Run all pending migrations
    python -m app.db.migrate --rollback   # Rollback last migration (not implemented)
    python -m app.db.migrate --status     # Show migration status
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def get_db_connection():
    """Create database connection from environment variables."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'observatory'),
            user=os.getenv('POSTGRES_USER', 'observatory'),
            password=os.getenv('POSTGRES_PASSWORD', 'changeme')
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Failed to connect to database: {e}")
        print("\nMake sure PostgreSQL is running:")
        print("  cd infra && docker compose up -d postgres")
        sys.exit(1)


def create_migrations_table(conn):
    """Create migrations tracking table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT NOW(),
                success BOOLEAN DEFAULT true,
                error_message TEXT
            )
        """)
    conn.commit()
    print("✓ Migrations tracking table ready")


def get_applied_migrations(conn):
    """Get list of already applied migrations."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT migration_name FROM schema_migrations
            WHERE success = true
            ORDER BY applied_at
        """)
        return {row[0] for row in cur.fetchall()}


def get_pending_migrations(migrations_dir, applied_migrations):
    """Get list of pending migrations."""
    migration_files = sorted(migrations_dir.glob('*.sql'))
    pending = []

    for migration_file in migration_files:
        if migration_file.name not in applied_migrations:
            pending.append(migration_file)

    return pending


def run_migration(conn, migration_file):
    """Run a single migration file."""
    print(f"\n🔄 Running migration: {migration_file.name}")

    # Read migration SQL
    with open(migration_file, 'r') as f:
        sql = f.read()

    # Execute migration
    try:
        with conn.cursor() as cur:
            # Execute the migration
            cur.execute(sql)

            # Record successful migration
            cur.execute("""
                INSERT INTO schema_migrations (migration_name, applied_at, success)
                VALUES (%s, %s, %s)
            """, (migration_file.name, datetime.now(), True))

        conn.commit()
        print(f"✅ {migration_file.name} completed successfully")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ {migration_file.name} failed: {e}")

        # Record failed migration
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO schema_migrations (migration_name, applied_at, success, error_message)
                    VALUES (%s, %s, %s, %s)
                """, (migration_file.name, datetime.now(), False, str(e)))
            conn.commit()
        except:
            pass

        return False


def show_migration_status(conn, migrations_dir):
    """Show status of all migrations."""
    applied_migrations = get_applied_migrations(conn)
    all_migration_files = sorted(migrations_dir.glob('*.sql'))

    print("\n📊 Migration Status")
    print("=" * 80)

    if not all_migration_files:
        print("No migration files found.")
        return

    for migration_file in all_migration_files:
        status = "✅ Applied" if migration_file.name in applied_migrations else "⏳ Pending"
        print(f"{status:15} {migration_file.name}")

    # Show detailed info from tracking table
    with conn.cursor() as cur:
        cur.execute("""
            SELECT migration_name, applied_at, success, error_message
            FROM schema_migrations
            ORDER BY applied_at DESC
            LIMIT 10
        """)
        rows = cur.fetchall()

        if rows:
            print("\n📜 Recent Migration History")
            print("=" * 80)
            for name, applied_at, success, error in rows:
                status = "✅" if success else "❌"
                print(f"{status} {name:40} {applied_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if error:
                    print(f"   Error: {error}")


def run_all_migrations():
    """Run all pending migrations."""
    # Get migrations directory
    migrations_dir = Path(__file__).parent / 'migrations'

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    print("🚀 Observatory Global - Database Migration Runner")
    print("=" * 80)

    # Connect to database
    print(f"📡 Connecting to database...")
    conn = get_db_connection()
    print(f"✓ Connected to: {os.getenv('POSTGRES_DB', 'observatory')}")

    # Create migrations tracking table
    create_migrations_table(conn)

    # Get pending migrations
    applied_migrations = get_applied_migrations(conn)
    pending_migrations = get_pending_migrations(migrations_dir, applied_migrations)

    if not pending_migrations:
        print("\n✅ All migrations are up to date!")
        show_migration_status(conn, migrations_dir)
        conn.close()
        return

    print(f"\n📋 Found {len(pending_migrations)} pending migration(s):")
    for migration in pending_migrations:
        print(f"   - {migration.name}")

    # Confirm before running
    response = input("\n🤔 Do you want to run these migrations? [y/N]: ")
    if response.lower() != 'y':
        print("❌ Migration cancelled")
        conn.close()
        sys.exit(0)

    # Run each pending migration
    success_count = 0
    for migration_file in pending_migrations:
        if run_migration(conn, migration_file):
            success_count += 1
        else:
            print("\n⚠️  Migration failed. Stopping to prevent further issues.")
            break

    # Summary
    print("\n" + "=" * 80)
    print(f"📊 Migration Summary: {success_count}/{len(pending_migrations)} successful")

    if success_count == len(pending_migrations):
        print("🎉 All migrations completed successfully!")
    else:
        print("⚠️  Some migrations failed. Please fix errors and try again.")

    conn.close()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == '--status':
            # Show migration status
            migrations_dir = Path(__file__).parent / 'migrations'
            conn = get_db_connection()
            create_migrations_table(conn)
            show_migration_status(conn, migrations_dir)
            conn.close()

        elif command == '--rollback':
            print("❌ Rollback not yet implemented")
            print("To manually rollback, drop tables and re-run migrations.")
            sys.exit(1)

        elif command == '--help':
            print(__doc__)
            sys.exit(0)

        else:
            print(f"Unknown command: {command}")
            print("Use --help for usage information")
            sys.exit(1)
    else:
        # Run all pending migrations
        run_all_migrations()


if __name__ == '__main__':
    main()
