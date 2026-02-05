"""
Accounts management routes.
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.dependencies import get_db
from src.repositories import AccountRepository, VideoRepository

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/accounts")
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


@router.post("/accounts/add")
async def add_account(
    request: Request,
    db: AsyncSession = Depends(get_db),
    username: str = Form(...),
):
    """Add a new Instagram account to track."""
    account_repo = AccountRepository(db)

    # Check if account already exists
    existing = await account_repo.get_by_username(username)
    if existing:
        return RedirectResponse(
            url="/accounts?error=Account+already+exists", status_code=303
        )

    # Create new account
    try:
        await account_repo.create(
            username=username,
            profile_url=f"https://www.instagram.com/{username}/",
            followers_count=0,
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        return RedirectResponse(
            url=f"/accounts?error=Failed+to+add+account:+{str(e)}", status_code=303
        )

    return RedirectResponse(url="/accounts", status_code=303)


@router.get("/accounts/bulk")
async def bulk_import_form(request: Request):
    """Show bulk import form."""
    return templates.TemplateResponse("accounts/bulk.html", {"request": request})


@router.post("/accounts/bulk")
async def bulk_import_accounts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    usernames_data: str = Form(...),
):
    """Process bulk import of Instagram accounts."""
    account_repo = AccountRepository(db)

    # Parse usernames (split by newline or comma, trim, skip empty)
    usernames = [u.strip() for u in usernames_data.replace(',', '\n').split('\n')]
    usernames = [u for u in usernames if u]

    results = {"added": 0, "skipped": 0, "errors": []}

    for username in usernames:
        existing = await account_repo.get_by_username(username)
        if existing:
            results["skipped"] += 1
        else:
            try:
                await account_repo.create(
                    username=username,
                    profile_url=f"https://www.instagram.com/{username}/",
                    followers_count=0,
                )
                results["added"] += 1
            except Exception as e:
                results["errors"].append(f"{username}: {str(e)}")

    await db.commit()
    return templates.TemplateResponse("accounts/bulk_result.html", {
        "request": request,
        "results": results
    })


@router.get("/accounts/{account_id}")
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
