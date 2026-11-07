"""
Billing routes for FixSec AI: Stripe subscriptions, plan management and webhooks.
"""
import json
import logging
from datetime import datetime, timedelta

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from core.billing import BillingManager, BillingNotConfigured, get_billing_manager
from db.models import Repository, Scan, User
from db.session import get_db
from routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

NOT_CONFIGURED = "Billing is not configured on this server yet."


class SubscriptionRequest(BaseModel):
    plan_id: str


@router.get("/plans")
def get_plans():
    return {"success": True, "plans": BillingManager.public_plans()}


@router.get("/subscription")
def get_user_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    billing = get_billing_manager(db)
    subscription = billing.get_user_subscription(current_user.id)
    plan = {k: v for k, v in billing.get_user_plan(current_user.id).items() if k != "stripe_price_id"}
    return {
        "success": True,
        "subscription": {
            "plan_id": subscription.plan_id if subscription else "free",
            "status": subscription.status if subscription else "active",
            "cancel_at_period_end": bool(subscription.cancel_at_period_end) if subscription else False,
            "current_period_end": subscription.current_period_end.isoformat()
            if subscription and subscription.current_period_end
            else None,
        },
        "plan": plan,
    }


@router.post("/subscribe")
def create_subscription(
    request: SubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a Stripe URL where the user can buy or change a plan."""
    billing = get_billing_manager(db)
    if request.plan_id not in billing.PLANS or request.plan_id == "free":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan ID")

    try:
        checkout_url = billing.create_checkout_session(
            user_id=current_user.id,
            plan_id=request.plan_id,
            success_url=f"{settings.FRONTEND_URL}/billing/success",
            cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",
        )
    except BillingNotConfigured:
        if current_user.github_id == "demo-user-dev":
            billing.set_user_plan(current_user.id, request.plan_id)
            return {"success": True, "checkout_url": f"{settings.FRONTEND_URL}/billing/success"}
        raise HTTPException(status_code=503, detail=NOT_CONFIGURED)
    except stripe.StripeError as exc:
        logger.warning("Stripe checkout failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach Stripe. Please try again.")
    return {"success": True, "checkout_url": checkout_url}


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        canceled = get_billing_manager(db).cancel_subscription(current_user.id)
    except BillingNotConfigured:
        if current_user.github_id == "demo-user-dev":
            get_billing_manager(db).set_user_plan(current_user.id, "free")
            return {"success": True, "message": "Demo subscription reset to free plan."}
        raise HTTPException(status_code=503, detail=NOT_CONFIGURED)
    except stripe.StripeError as exc:
        logger.warning("Stripe cancel failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach Stripe. Please try again.")
    if not canceled:
        raise HTTPException(status_code=400, detail="No active subscription to cancel")
    return {"success": True, "message": "Your plan stays active until the end of the billing period."}


@router.get("/portal")
def get_billing_portal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        portal_url = get_billing_manager(db).get_billing_portal_url(
            current_user.id, f"{settings.FRONTEND_URL}/billing"
        )
    except BillingNotConfigured:
        if current_user.github_id == "demo-user-dev":
            return {"success": True, "portal_url": f"{settings.FRONTEND_URL}/billing"}
        raise HTTPException(status_code=503, detail=NOT_CONFIGURED)
    except stripe.StripeError as exc:
        logger.warning("Stripe portal failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach Stripe. Please try again.")
    if not portal_url:
        raise HTTPException(status_code=400, detail="No active subscription found")
    return {"success": True, "portal_url": portal_url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Verify and apply Stripe events."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail=NOT_CONFIGURED)

    payload = await request.body()
    try:
        stripe.Webhook.construct_event(
            payload, request.headers.get("stripe-signature"), settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = json.loads(payload)
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    billing = get_billing_manager(db)

    if event_type == "checkout.session.completed":
        billing.handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        billing.sync_subscription(data)
    elif event_type == "customer.subscription.deleted":
        billing.mark_subscription_status(data.get("id"), "canceled")
    elif event_type == "invoice.payment_failed":
        billing.mark_subscription_status(data.get("subscription"), "past_due")

    return {"success": True}


@router.get("/usage")
def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    billing = get_billing_manager(db)
    plan = billing.get_user_plan(current_user.id)
    repo_count = db.query(Repository).filter(Repository.user_id == current_user.id).count()
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    scans_this_month = (
        db.query(Scan)
        .join(Repository)
        .filter(Repository.user_id == current_user.id, Scan.started_at >= month_start)
        .count()
    )
    return {
        "success": True,
        "usage": {
            "repositories": {
                "current": repo_count,
                "limit": plan["repos_limit"],
                "unlimited": plan["repos_limit"] is None,
            },
            "scans_today": {
                "current": billing.count_scans_today(current_user.id),
                "limit": plan["scans_per_day"],
                "unlimited": plan["scans_per_day"] is None,
            },
            "scans_this_month": scans_this_month,
        },
    }


@router.get("/check-limits/{action}")
def check_limits(
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    billing = get_billing_manager(db)
    if action == "add_repo":
        count = db.query(Repository).filter(Repository.user_id == current_user.id).count()
        allowed = billing.check_repo_limit(current_user.id, count)
    elif action == "scan":
        allowed = billing.check_scan_limit(current_user.id)
    elif action == "auto_fix":
        allowed = billing.can_use_auto_fix(current_user.id)
    elif action == "scheduled_scans":
        allowed = billing.can_use_scheduled_scans(current_user.id)
    elif action == "slack_alerts":
        allowed = billing.can_use_slack_alerts(current_user.id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")
    return {"success": True, "allowed": allowed}
