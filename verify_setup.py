"""
Quick verification script to check if the admin panel setup is working.
"""
import asyncio
from src.database.session import get_session
from src.models import WorkerHeartbeat
from sqlalchemy import select


async def verify_setup():
    """Verify that WorkerHeartbeat table exists and is accessible."""
    print("=" * 60)
    print("ADMIN PANEL SETUP VERIFICATION")
    print("=" * 60)

    try:
        async with get_session() as session:
            # Try to query the worker_heartbeats table
            result = await session.execute(select(WorkerHeartbeat))
            heartbeats = result.scalars().all()

            print("\n✅ Database connection: SUCCESS")
            print(f"✅ WorkerHeartbeat table: EXISTS")
            print(f"✅ Found {len(heartbeats)} heartbeat record(s)")

            if heartbeats:
                for hb in heartbeats:
                    print(f"\n   Worker: {hb.worker_name}")
                    print(f"   Status: {hb.status}")
                    print(f"   Last Heartbeat: {hb.last_heartbeat}")
                    print(f"   PID: {hb.pid}")
            else:
                print("\n⚠️  No heartbeat records found")
                print("   This is normal if unified_worker.py hasn't been started yet")

            print("\n" + "=" * 60)
            print("NEXT STEPS:")
            print("=" * 60)
            print("1. Start the worker: python unified_worker.py")
            print("2. In another terminal: python run_admin.py")
            print("3. Open: http://localhost:8000/dashboard")
            print("=" * 60)

            return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible issues:")
        print("  - Database not running")
        print("  - Wrong credentials in .env")
        print("  - Migration not applied (run: alembic upgrade head)")
        return False


if __name__ == "__main__":
    result = asyncio.run(verify_setup())
    exit(0 if result else 1)
