#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick script to toggle TEST_MODE in .env file

Usage:
    python toggle_test_mode.py          # Show current mode
    python toggle_test_mode.py on       # Enable test mode
    python toggle_test_mode.py off      # Disable test mode
"""
import sys
import os
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_env_path():
    """Get path to .env file."""
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Please create .env file first:")
        print("   cp .env.example .env")
        sys.exit(1)
    return env_path


def read_env(env_path):
    """Read .env file and return lines."""
    with open(env_path, 'r', encoding='utf-8') as f:
        return f.readlines()


def write_env(env_path, lines):
    """Write lines to .env file."""
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def get_test_mode(lines):
    """Check if TEST_MODE is enabled."""
    for line in lines:
        if line.strip().startswith('TEST_MODE='):
            value = line.split('=')[1].strip().lower()
            return value == 'true'
    return False  # Default if not set


def set_test_mode(env_path, lines, enabled):
    """Set TEST_MODE in .env file."""
    new_lines = []
    found = False

    for line in lines:
        if line.strip().startswith('TEST_MODE='):
            found = True
            if enabled:
                new_lines.append('TEST_MODE=true\n')
            else:
                new_lines.append('TEST_MODE=false\n')
        else:
            new_lines.append(line)

    # If TEST_MODE not found, add it
    if not found:
        new_lines.append(f'\nTEST_MODE={"true" if enabled else "false"}\n')

    write_env(env_path, new_lines)
    return found


def show_status():
    """Show current TEST_MODE status."""
    env_path = get_env_path()
    lines = read_env(env_path)
    is_enabled = get_test_mode(lines)

    print("=" * 60)
    print("CURRENT TEST_MODE STATUS")
    print("=" * 60)

    if is_enabled:
        print("🔴 TEST_MODE: ENABLED")
        print("\n⚠️  Intervals:")
        print("   • Fetch videos: every 10 seconds")
        print("   • Update schedules: every 30 seconds")
        print("   • Process metrics: every 10 seconds")
        print("\n⚠️  WARNING: This is for testing only!")
    else:
        print("✅ TEST_MODE: DISABLED")
        print("\n✅ Production intervals:")
        print("   • Fetch videos: every 6 hours")
        print("   • Update schedules: every 1 hour")
        print("   • Process metrics: every 1 minute")

    print("\n" + "=" * 60)
    print("Commands:")
    print("  python toggle_test_mode.py on   - Enable test mode")
    print("  python toggle_test_mode.py off  - Disable test mode")
    print("=" * 60)

    return 0


def enable_test_mode():
    """Enable TEST_MODE."""
    env_path = get_env_path()
    lines = read_env(env_path)

    if get_test_mode(lines):
        print("✅ TEST_MODE is already enabled")
        return 0

    set_test_mode(env_path, lines, True)
    print("✅ TEST_MODE enabled!")
    print("\n🔴 New intervals:")
    print("   • Fetch videos: every 10 seconds")
    print("   • Update schedules: every 30 seconds")
    print("   • Process metrics: every 10 seconds")
    print("\n⚠️  Restart worker to apply changes:")
    print("   python unified_worker.py")
    return 0


def disable_test_mode():
    """Disable TEST_MODE."""
    env_path = get_env_path()
    lines = read_env(env_path)

    if not get_test_mode(lines):
        print("✅ TEST_MODE is already disabled")
        return 0

    set_test_mode(env_path, lines, False)
    print("✅ TEST_MODE disabled!")
    print("\n✅ Production intervals restored:")
    print("   • Fetch videos: every 6 hours")
    print("   • Update schedules: every 1 hour")
    print("   • Process metrics: every 1 minute")
    print("\n✅ Restart worker to apply changes:")
    print("   python unified_worker.py")
    return 0


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # No argument - show status
        return show_status()
    elif sys.argv[1].lower() in ['on', 'true', '1', 'enable', 'yes']:
        return enable_test_mode()
    elif sys.argv[1].lower() in ['off', 'false', '0', 'disable', 'no']:
        return disable_test_mode()
    elif sys.argv[1].lower() in ['status', 'check', 'show']:
        return show_status()
    else:
        print(f"❌ Unknown command: {sys.argv[1]}")
        print("\nUsage:")
        print("  python toggle_test_mode.py          # Show status")
        print("  python toggle_test_mode.py on       # Enable test mode")
        print("  python toggle_test_mode.py off      # Disable test mode")
        print("  python toggle_test_mode.py status   # Show status")
        return 1


if __name__ == "__main__":
    sys.exit(main())
