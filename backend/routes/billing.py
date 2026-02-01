"""
Billing routes for FixSec AI
Handles Stripe subscriptions, plan management, and webhooks
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any
import stripe
import json

from db.session import get_db
from routes.auth import get_current_user
from db.models import User
from core.billing import get_billing_manager, BillingManager
from config import settings

router = APIRouter()

class SubscriptionRequest(BaseModel):
    plan_id: str

class BillingResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = {}

@router.get("/plans")
async def get_plans():
    """Get available subscription plans"""
    billing_manager = BillingManager(None)  # No DB needed for static data
    
    return {
        "success": True,
        "plans": billing_manager.PLANS
    }

@router.get("/subscription")
async def get_user_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's current subscription details"""
    billing_manager = get_billing_manager(db)
    
    subscription = billing_manager.get_user_subscription(current_user.id)
    plan = billing_manager.get_user_plan(current_user.id)
    
    return {
        "success": True,
        "subscription": {
            "plan_id": subscription.plan_id if subscription else "free",
            "status": subscription.status if subscription else "active",
            "current_period_end": subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None
        },
        "plan": plan,
        "limits": {
            "repos_limit": plan['repos_limit'],
            "scans_per_day": plan['scans_per_day'],
            "auto_fix": plan['auto_fix'],
            "scheduled_scans": plan['scheduled_scans'],
            "slack_alerts": plan['slack_alerts']
        }
    }

@router.post("/subscribe")
async def create_subscription(
    request: SubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for subscription"""
    billing_manager = get_billing_manager(db)
    
    if request.plan_id not in billing_manager.PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan ID"
        )
    
    if request.plan_id == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot subscribe to free plan"
        )
    
    try:
        success_url = f"{settings.FRONTEND_URL}/billing/success"
        cancel_url = f"{settings.FRONTEND_URL}/billing/cancel"
        
        checkout_url = billing_manager.create_checkout_session(
            user_id=current_user.id,
            plan_id=request.plan_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return {
            "success": True,
            "checkout_url": checkout_url
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )

@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel user's subscription"""
    billing_manager = get_billing_manager(db)
    
    success = billing_manager.cancel_subscription(current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel"
        )
    
    return {
        "success": True,
        "message": "Subscription canceled successfully"
    }

@router.get("/portal")
async def get_billing_portal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Stripe customer portal URL"""
    billing_manager = get_billing_manager(db)
    
    return_url = f"{settings.FRONTEND_URL}/billing"
    portal_url = billing_manager.get_billing_portal_url(current_user.id, return_url)
    
    if not portal_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found"
        )
    
    return {
        "success": True,
        "portal_url": portal_url
    }

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    billing_manager = get_billing_manager(db)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        billing_manager.handle_successful_payment(session['id'])
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        # Handle subscription updates (plan changes, etc.)
        pass
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Handle subscription cancellation
        pass
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        # Handle failed payments
        pass
    
    return {"success": True}

@router.get("/usage")
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's current usage statistics"""
    from db.models import Repository, Scan
    from datetime import datetime, timedelta
    
    billing_manager = get_billing_manager(db)
    plan = billing_manager.get_user_plan(current_user.id)
    
    # Count repositories
    repo_count = db.query(Repository).filter(Repository.user_id == current_user.id).count()
    
    # Count scans today
    today = datetime.utcnow().date()
    scans_today = db.query(Scan).join(Repository).filter(
        Repository.user_id == current_user.id,
        Scan.started_at >= today,
        Scan.started_at < today + timedelta(days=1)
    ).count()
    
    # Count total scans this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    scans_this_month = db.query(Scan).join(Repository).filter(
        Repository.user_id == current_user.id,
        Scan.started_at >= month_start
    ).count()
    
    return {
        "success": True,
        "usage": {
            "repositories": {
                "current": repo_count,
                "limit": plan['repos_limit'],
                "unlimited": plan['repos_limit'] is None
            },
            "scans_today": {
                "current": scans_today,
                "limit": plan['scans_per_day'],
                "unlimited": plan['scans_per_day'] is None
            },
            "scans_this_month": scans_this_month
        },
        "plan": plan
    }

@router.get("/check-limits/{action}")
async def check_limits(
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user can perform a specific action based on their plan"""
    billing_manager = get_billing_manager(db)
    
    if action == "add_repo":
        from db.models import Repository
        current_repos = db.query(Repository).filter(Repository.user_id == current_user.id).count()
        allowed = billing_manager.check_repo_limit(current_user.id, current_repos)
        
    elif action == "scan":
        allowed = billing_manager.check_scan_limit(current_user.id)
        
    elif action == "auto_fix":
        allowed = billing_manager.can_use_auto_fix(current_user.id)
        
    elif action == "scheduled_scans":
        allowed = billing_manager.can_use_scheduled_scans(current_user.id)
        
    elif action == "slack_alerts":
        allowed = billing_manager.can_use_slack_alerts(current_user.id)
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action"
        )
    
    return {
        "success": True,
        "allowed": allowed,
        "plan": billing_manager.get_user_plan(current_user.id)
    }