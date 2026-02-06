"""
Enrich usernames.json with Instagram user_pk values.

This script reads usernames from a JSON file, resolves them to user_pk values,
and saves the results to a new JSON file. It supports deduplication, resume
capability, and detailed progress tracking.

REQUIRES AUTHENTICATION via Instagram credentials.

Usage:
    python scripts/enrich_usernames_json.py
    python scripts/enrich_usernames_json.py --delay 2
    python scripts/enrich_usernames_json.py --force
"""

import asyncio
import json
from pathlib import Path
import sys
import time
from argparse import ArgumentParser
from datetime import timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.instagram_service import InstagramService


class UsernameEnricher:
    """Class for enriching usernames.json with user_pk values."""

    def __init__(self, input_file: str, output_file: str, delay: float = 1.5):
        """Initialize the enricher.

        Args:
            input_file: Path to input JSON file with usernames
            output_file: Path to output JSON file with usernames and user_pk
            delay: Delay between requests in seconds
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.delay = delay
        self.results = []
        self.processed_usernames = set()

    def load_input(self) -> list:
        """Load usernames from input file.

        Returns:
            List of usernames (strings)
        """
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # If this is an array of strings - usernames
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], str):
                return data  # Array of strings
            elif isinstance(data[0], dict):
                return [item.get('username') for item in data]  # Array of objects

        return []

    def deduplicate(self, usernames: list) -> tuple[list, int]:
        """Remove duplicates while preserving first occurrence order.

        Args:
            usernames: List of usernames (may contain duplicates)

        Returns:
            Tuple of (unique_usernames, duplicate_count)
        """
        seen = set()
        unique = []
        duplicates = 0

        for username in usernames:
            if username not in seen:
                seen.add(username)
                unique.append(username)
            else:
                duplicates += 1

        return unique, duplicates

    def load_existing_results(self) -> dict:
        """Load existing results from output file.

        Returns:
            Dict mapping username to user_pk (or None if failed)
        """
        if not self.output_file.exists():
            return {}

        with open(self.output_file, 'r', encoding='utf-8') as f:
            results = json.load(f)

        return {r['username']: r.get('user_pk') for r in results}

    async def enrich(self, force: bool = False):
        """Main enrichment method (requires authentication).

        Args:
            force: If True, ignore existing output file and start from beginning
        """
        # Load usernames
        usernames = self.load_input()
        print(f"Loaded {len(usernames)} usernames from {self.input_file}")

        # Deduplicate
        usernames, dup_count = self.deduplicate(usernames)
        if dup_count > 0:
            print(f"Found {dup_count} duplicate usernames (will be removed)")
        print(f"Processing {len(usernames)} unique usernames\n")

        # Load existing results
        if not force:
            existing = self.load_existing_results()
            if existing:
                print(f"Existing output file found: {self.output_file}")
                print(f"Already processed: {len(existing)} usernames")
                self.processed_usernames = set(existing.keys())
                self.results = [
                    {"username": uname, "user_pk": pk}
                    for uname, pk in existing.items()
                ]
                print(f"Continuing from last processed username...\n")
        else:
            print("Force mode: starting from beginning\n")

        # Initialize Instagram service
        instagram_service = InstagramService()

        try:
            # Authenticate
            print("Authenticating with Instagram...")
            await instagram_service._authenticate_client()
            print("✓ Authenticated successfully\n")

            # Process usernames
            start_time = time.time()
            success_count = len(self.processed_usernames)
            error_count = 0

            for idx, username in enumerate(usernames, 1):
                # Skip if already processed
                if username in self.processed_usernames:
                    continue

                try:
                    # Show progress
                    self.print_progress(
                        idx, len(usernames), username,
                        success_count, error_count, start_time
                    )

                    # Get user_pk
                    def _get_user_id(client, username: str) -> int:
                        return client.user_id_from_username(username)

                    user_pk = await instagram_service._execute_instagram_request(_get_user_id, username)

                    self.results.append({
                        "username": username,
                        "user_pk": user_pk
                    })
                    success_count += 1

                    print(f"   → user_pk: {user_pk}")

                    # Rate limiting
                    await asyncio.sleep(self.delay)

                except Exception as e:
                    error_count += 1
                    self.results.append({
                        "username": username,
                        "user_pk": None,
                        "error": str(e)
                    })
                    print(f"   ✗ Error: {e}")

            # Final report
            elapsed = time.time() - start_time
            self.print_final_report(len(usernames), success_count, error_count, elapsed)

        finally:
            await instagram_service.close()

    def save_results(self):
        """Save results to output file."""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Results saved to {self.output_file}")

    def print_progress(self, current: int, total: int, username: str,
                      success_count: int, error_count: int, start_time: float):
        """Print progress bar with ETA.

        Args:
            current: Current index (1-based)
            total: Total number of items
            username: Current username being processed
            success_count: Number of successful resolutions so far
            error_count: Number of errors so far
            start_time: Time when processing started
        """
        elapsed = time.time() - start_time
        if current > 0:
            eta = (elapsed / current) * (total - current)
        else:
            eta = 0

        print(f"[{current}/{total}] Processing: {username}")
        print(f"   Progress: {current/total*100:.1f}% | "
              f"ETA: {self.format_time(eta)} | "
              f"Success: {success_count} | Errors: {error_count}")

    def print_final_report(self, total: int, success: int, errors: int, elapsed: float):
        """Print final report.

        Args:
            total: Total number of usernames
            success: Number of successful resolutions
            errors: Number of failed resolutions
            elapsed: Time taken in seconds
        """
        print("\n" + "=" * 80)
        print("ENRICHMENT COMPLETE")
        print("=" * 80)
        print(f"Total usernames: {total}")
        print(f"Successfully resolved: {success}")
        print(f"Failed: {errors}")
        print(f"Time taken: {self.format_time(elapsed)}")
        print("=" * 80)

        if errors > 0:
            print("\nFailed usernames:")
            for r in self.results:
                if not r.get('user_pk'):
                    error = r.get('error', 'Unknown error')
                    print(f"  - @{r['username']}: {error}")

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds to human-readable format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string (e.g., "1h 23m 45s")
        """
        td = timedelta(seconds=int(seconds))
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"


def main():
    """Main entry point."""
    parser = ArgumentParser(
        description="Enrich usernames.json with Instagram user_pk values"
    )
    parser.add_argument(
        "--input",
        default="usernames.json",
        help="Input JSON file with usernames (default: usernames.json)"
    )
    parser.add_argument(
        "--output",
        default="usernames_with_pks.json",
        help="Output JSON file with usernames and user_pk (default: usernames_with_pks.json)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force restart, ignore existing output file"
    )

    args = parser.parse_args()

    # Check input file
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Create enricher
    enricher = UsernameEnricher(args.input, args.output, args.delay)

    # Run enrichment
    asyncio.run(enricher.enrich(force=args.force))

    # Save results
    enricher.save_results()


if __name__ == "__main__":
    main()
