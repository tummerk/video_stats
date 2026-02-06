"""
Get Instagram user_pk values from a list of usernames.

This script reads usernames from a file (one per line) and resolves them to user_pk values.
Output can be saved as JSON for later use with init_accounts.py.

Usage:
    python scripts/get_user_pks.py usernames.txt -o output.json
"""
import asyncio
import json
from pathlib import Path
import sys
from argparse import ArgumentParser

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.instagram_service import InstagramService
from src.config import settings


async def get_user_pks(usernames: list[str]) -> list[dict]:
    """Resolve usernames to user_pk values.

    Args:
        usernames: List of Instagram usernames (without @)

    Returns:
        List of dicts with username and user_pk
    """
    # Initialize Instagram service
    instagram_service = InstagramService()

    try:
        # Authenticate
        print("Authenticating with Instagram...")
        await instagram_service._authenticate_client()
        print("✓ Authenticated successfully\n")

        results = []

        for idx, username in enumerate(usernames, 1):
            username = username.strip().lstrip('@')
            if not username:
                continue

            try:
                print(f"[{idx}/{len(usernames)}] Resolving @{username}...")

                # Use instagrapi's user_id_from_username method
                def _get_user_id(client, username: str) -> int:
                    return client.user_id_from_username(username)

                user_pk = await instagram_service._execute_instagram_request(_get_user_id, username)

                result = {
                    "username": username,
                    "user_pk": user_pk
                }
                results.append(result)

                print(f"  → user_pk: {user_pk}")

                # Rate limiting: 1 second between requests
                await asyncio.sleep(1)

            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append({
                    "username": username,
                    "user_pk": None,
                    "error": str(e)
                })

        return results

    finally:
        await instagram_service.close()


def main():
    parser = ArgumentParser(description="Get Instagram user_pk values from usernames")
    parser.add_argument("input_file", help="File with usernames (one per line)")
    parser.add_argument("-o", "--output", default="user_pks.json", help="Output JSON file (default: user_pks.json)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    args = parser.parse_args()

    # Read usernames from file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {args.input_file}")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        usernames = [line.strip() for line in f if line.strip()]

    if not usernames:
        print("Error: No usernames found in file")
        sys.exit(1)

    print(f"Loaded {len(usernames)} usernames from {args.input_file}\n")

    # Resolve usernames
    results = asyncio.run(get_user_pks(usernames))

    # Save results
    if args.format == "json":
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Results saved to {args.output}")

        # Print summary
        successful = sum(1 for r in results if r.get("user_pk"))
        failed = len(results) - successful

        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total:     {len(results)}")
        print(f"Success:   {successful}")
        print(f"Failed:    {failed}")

        if failed > 0:
            print("\nFailed usernames:")
            for r in results:
                if not r.get("user_pk"):
                    print(f"  - @{r['username']}: {r.get('error', 'Unknown error')}")

    elif args.format == "csv":
        import csv
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["username", "user_pk", "error"])
            writer.writeheader()
            writer.writerows(results)

        print(f"\n✓ Results saved to {args.output}")


if __name__ == "__main__":
    main()
