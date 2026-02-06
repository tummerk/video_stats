"""
Accounts management routes.
"""
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.dependencies import get_db
from src.repositories import AccountRepository, VideoRepository

router = APIRouter()
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/")
async def list_accounts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    offset: int = 0,
    limit: int = 50,
):
    """List all accounts with video counts."""
    account_repo = AccountRepository(db)

    accounts = await account_repo.get_with_video_stats(limit=limit, offset=offset)
    total_accounts = await account_repo.count_all()

    return templates.TemplateResponse(
        "accounts/list.html",
        {
            "request": request,
            "accounts": accounts,
            "total": total_accounts,
            "offset": offset,
            "limit": limit,
        },
    )


@router.post("/add")
async def add_account(
    request: Request,
    db: AsyncSession = Depends(get_db),
    username: str = Form(...),
    user_pk: str = Form(None),
):
    """Add a new Instagram account to track."""
    import json
    account_repo = AccountRepository(db)

    # Try to parse as JSON first
    try:
        data = json.loads(username)
        if isinstance(data, list) and len(data) > 0:
            # Bulk import from JSON array
            results = {"added": 0, "skipped": 0, "errors": []}
            try:
                for item in data:
                    try:
                        acc_username = item.get("username")
                        acc_user_pk = item.get("user_pk")

                        if not acc_username or not acc_user_pk:
                            results["errors"].append(f"{item}: Missing username or user_pk")
                            continue

                        # Check if account already exists
                        existing = await account_repo.get(acc_user_pk)
                        if existing:
                            results["skipped"] += 1
                        else:
                            await account_repo.create(
                                id=acc_user_pk,
                                username=acc_username,
                                profile_url=f"https://www.instagram.com/{acc_username}/",
                                followers_count=0,
                            )
                            results["added"] += 1
                    except Exception as e:
                        results["errors"].append(f"{item}: {str(e)}")

                await db.commit()
                return templates.TemplateResponse("accounts/bulk_result.html", {
                    "request": request,
                    "results": results
                })
            except Exception as e:
                await db.rollback()
                return RedirectResponse(
                    url=f"/accounts?error=Bulk+import+failed:+{str(e)}", status_code=303
                )
    except (json.JSONDecodeError, TypeError, ValueError):
        # Not JSON, proceed with single account
        pass

    # Single account add (backwards compatibility)
    # Only proceed if username is not too long (not JSON text)
    if len(username) > 150:
        return RedirectResponse(
            url="/accounts?error=Username+too+long.+Use+Bulk+Import+for+JSON+data", status_code=303
        )

    check_existing = await account_repo.get_by_username(username)
    if check_existing:
        return RedirectResponse(
            url="/accounts?error=Account+already+exists", status_code=303
        )

    # Create new account
    try:
        account_data = {
            "username": username,
            "profile_url": f"https://www.instagram.com/{username}/",
            "followers_count": 0,
        }

        if user_pk:
            account_data["id"] = int(user_pk)

        await account_repo.create(**account_data)
        await db.commit()
    except Exception as e:
        await db.rollback()
        return RedirectResponse(
            url=f"/accounts?error=Failed+to+add+account:+{str(e)}", status_code=303
        )

    return RedirectResponse(url="/accounts", status_code=303)


@router.get("/bulk")
async def bulk_import_form(request: Request):
    """Show bulk import form."""
    return templates.TemplateResponse("accounts/bulk.html", {"request": request})


@router.post("/bulk")
async def bulk_import_accounts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    usernames_data: str = Form(...),
):
    """Process bulk import of Instagram accounts.

    Supports two formats:
    1. JSON array with username and user_pk: [{"username": "user1", "user_pk": 123}, ...]
    2. Plain text with usernames (one per line or comma-separated)
    """
    import json
    account_repo = AccountRepository(db)

    results = {"added": 0, "skipped": 0, "errors": []}

    try:
        # Try to parse as JSON first
        try:
            data = json.loads(usernames_data)
            if isinstance(data, list) and len(data) > 0:
                # JSON format with username and user_pk
                for item in data:
                    try:
                        acc_username = item.get("username")
                        acc_user_pk = item.get("user_pk")

                        if not acc_username or not acc_user_pk:
                            results["errors"].append(f"{str(item)[:100]}: Missing username or user_pk")
                            continue

                        # Check if account already exists by ID
                        existing = await account_repo.get(acc_user_pk)
                        if existing:
                            results["skipped"] += 1
                        else:
                            await account_repo.create(
                                id=acc_user_pk,
                                username=acc_username,
                                profile_url=f"https://www.instagram.com/{acc_username}/",
                                followers_count=0,
                            )
                            results["added"] += 1
                    except Exception as e:
                        results["errors"].append(f"{str(item)[:100]}: {str(e)[:100]}")

                await db.commit()
                return templates.TemplateResponse("accounts/bulk_result.html", {
                    "request": request,
                    "results": results
                })
        except (json.JSONDecodeError, TypeError, ValueError):
            # Not JSON, try plain text format
            pass

        # Plain text format (usernames only, one per line or comma-separated)
        usernames = [u.strip() for u in usernames_data.replace(',', '\n').split('\n')]
        usernames = [u for u in usernames if u]

        for username in usernames:
            try:
                existing = await account_repo.get_by_username(username)
                if existing:
                    results["skipped"] += 1
                else:
                    await account_repo.create(
                        username=username,
                        profile_url=f"https://www.instagram.com/{username}/",
                        followers_count=0,
                    )
                    results["added"] += 1
            except Exception as e:
                results["errors"].append(f"{username}: {str(e)[:100]}")

        await db.commit()
        return templates.TemplateResponse("accounts/bulk_result.html", {
            "request": request,
            "results": results
        })
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")


@router.get("/{account_id}")
async def account_detail(
    request: Request,
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """View account detail with videos."""
    account_repo = AccountRepository(db)
    video_repo = VideoRepository(db)

    account = await account_repo.get_by_id_with_videos(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    videos = await video_repo.get_by_account_id(
        account_id, limit=100, offset=0
    )

    return templates.TemplateResponse(
        "accounts/detail.html",
        {
            "request": request,
            "account": account,
            "videos": videos,
        },
    )
