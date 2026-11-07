"""
Stripe billing integration for FixSec AI.

Stripe is the source of truth for subscription state. Webhooks keep the local
Subscription row in sync; plan limits are enforced from that row.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import stripe
from sqlalchemy.orm import Session

from config import settings
from db.models import Repository, Scan, Subscription, User

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# Stripe statuses that keep paid features on. past_due is Stripe's retry window.
ENTITLED_STATUSES = ("active", "trialing", "past_due")


class BillingNotConfigured(Exception):
    """Stripe credentials or price IDs are missing on this server."""


class BillingManager:
    """Manages Stripe billing and subscription logic."""

    PLANS = {
        'free': {
            'name': 'Free',
            'price': 0,
            'price_inr': 0,
            'repos_limit': 1,
            'scans_per_day': 1,
            'auto_fix': False,
            'scheduled_scans': False,
            'slack_alerts': False,
            'stripe_price_id': None
        },
        'starter': {
            'name': 'Starter',
            'price': 25,
            'price_inr': 199,
            'repos_limit': 5,
            'scans_per_day': None,  # Unlimited
            'auto_fix': False,
            'scheduled_scans': False,
            'slack_alerts': False,
            'stripe_price_id': settings.STRIPE_STARTER_PRICE_ID
        },
        'pro': {
            'name': 'Professional',
            'price': 49,
            'price_inr': 499,
            'repos_limit': None,  # Unlimited
            'scans_per_day': None,
            'auto_fix': True,
            'scheduled_scans': False,
            'slack_alerts': False,
            'stripe_price_id': settings.STRIPE_PRO_PRICE_ID
        },
        'team': {
            'name': 'Team',
            'price': 99,
            'price_inr': 999,
            'repos_limit': None,  # Unlimited
            'scans_per_day': None,
            'auto_fix': True,
            'scheduled_scans': True,
            'slack_alerts': True,
            'stripe_price_id': settings.STRIPE_TEAM_PRICE_ID
        }
    }

    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def public_plans(cls) -> Dict[str, Dict[str, Any]]:
        return {
            plan_id: {key: value for key, value in plan.items() if key != 'stripe_price_id'}
            for plan_id, plan in cls.PLANS.items()
        }

    def set_user_plan(self, user_id: int, plan_id: str) -> Subscription:
        """Directly set or change user's plan for development, demo, or testing."""
        if plan_id not in self.PLANS:
            raise ValueError("Invalid plan ID")
        row = self.get_user_subscription(user_id)
        if row is None:
            row = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status="active",
                stripe_subscription_id=f"demo_sub_{user_id}_{plan_id}",
                current_period_end=datetime.utcnow() + timedelta(days=365),
            )
            self.db.add(row)
        else:
            row.plan_id = plan_id
            row.status = "active"
            row.current_period_end = datetime.utcnow() + timedelta(days=365)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        return (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.status.in_(ENTITLED_STATUSES))
            .order_by(Subscription.created_at.desc(), Subscription.id.desc())
            .first()
        )

    def get_user_plan(self, user_id: int) -> Dict[str, Any]:
        subscription = self.get_user_subscription(user_id)
        if not subscription:
            return self.PLANS['free']
        return self.PLANS.get(subscription.plan_id, self.PLANS['free'])

    def check_repo_limit(self, user_id: int, current_repos: int) -> bool:
        repos_limit = self.get_user_plan(user_id)['repos_limit']
        return repos_limit is None or current_repos < repos_limit

    def count_scans_today(self, user_id: int) -> int:
        """Failed scans do not use up the allowance."""
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(Scan)
            .join(Repository)
            .filter(
                Repository.user_id == user_id,
                Scan.started_at >= start_of_day,
                Scan.started_at < start_of_day + timedelta(days=1),
                Scan.status != 'failed',
            )
            .count()
        )

    def check_scan_limit(self, user_id: int) -> bool:
        scans_per_day = self.get_user_plan(user_id)['scans_per_day']
        return scans_per_day is None or self.count_scans_today(user_id) < scans_per_day

    def can_use_auto_fix(self, user_id: int) -> bool:
        return self.get_user_plan(user_id)['auto_fix']

    def can_use_scheduled_scans(self, user_id: int) -> bool:
        return self.get_user_plan(user_id)['scheduled_scans']

    def can_use_slack_alerts(self, user_id: int) -> bool:
        return self.get_user_plan(user_id)['slack_alerts']

    def create_checkout_session(
        self, user_id: int, plan_id: str, success_url: str, cancel_url: str
    ) -> str:
        """Return a URL where the user can buy, or change to, this plan."""
        if plan_id not in self.PLANS or plan_id == 'free':
            raise ValueError("Invalid plan ID")

        plan = self.PLANS[plan_id]
        if not settings.STRIPE_SECRET_KEY or not plan['stripe_price_id']:
            raise BillingNotConfigured()

        # A second checkout would bill a subscriber twice. Plan changes go
        # through the portal, which swaps the existing subscription.
        current = self.get_user_subscription(user_id)
        if current and current.stripe_subscription_id:
            portal_url = self.get_billing_portal_url(user_id, cancel_url)
            if portal_url:
                return portal_url

        user = self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        metadata = {'user_id': str(user_id), 'plan_id': plan_id}
        params: Dict[str, Any] = {
            'mode': 'subscription',
            'line_items': [{'price': plan['stripe_price_id'], 'quantity': 1}],
            'success_url': success_url + '?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': cancel_url,
            'client_reference_id': str(user_id),
            'metadata': metadata,
            'subscription_data': {'metadata': metadata},
        }
        if user.email:
            params['customer_email'] = user.email
        return stripe.checkout.Session.create(**params).url

    def handle_checkout_completed(self, session: Dict[str, Any]) -> bool:
        """Activate a subscription from a checkout.session.completed event."""
        subscription_id = session.get('subscription')
        metadata = session.get('metadata') or {}
        if not subscription_id or not metadata.get('user_id'):
            return False
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        if hasattr(stripe_subscription, 'to_dict'):
            stripe_subscription = stripe_subscription.to_dict()
        return self.sync_subscription(
            stripe_subscription,
            user_id=int(metadata['user_id']),
            plan_id=metadata.get('plan_id'),
        )

    def sync_subscription(
        self,
        stripe_subscription: Dict[str, Any],
        user_id: Optional[int] = None,
        plan_id: Optional[str] = None,
    ) -> bool:
        """Mirror a Stripe subscription object into the local row."""
        subscription_id = stripe_subscription.get('id')
        metadata = stripe_subscription.get('metadata') or {}
        row = (
            self.db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == subscription_id)
            .first()
        )

        if row is None:
            user_id = user_id or (int(metadata['user_id']) if metadata.get('user_id') else None)
            if user_id is None:
                logger.warning("Stripe subscription %s has no matching user", subscription_id)
                return False
            row = Subscription(
                user_id=user_id,
                plan_id=plan_id or metadata.get('plan_id') or 'free',
                stripe_subscription_id=subscription_id,
            )
            self.db.add(row)

        item = ((stripe_subscription.get('items') or {}).get('data') or [{}])[0]
        row.plan_id = self._plan_for_price(item) or plan_id or row.plan_id
        row.status = stripe_subscription.get('status', row.status)
        row.stripe_customer_id = stripe_subscription.get('customer') or row.stripe_customer_id
        row.cancel_at_period_end = bool(stripe_subscription.get('cancel_at_period_end'))

        # Newer Stripe API versions report the period on the subscription item.
        start = stripe_subscription.get('current_period_start') or item.get('current_period_start')
        end = stripe_subscription.get('current_period_end') or item.get('current_period_end')
        if start:
            row.current_period_start = datetime.utcfromtimestamp(start)
        if end:
            row.current_period_end = datetime.utcfromtimestamp(end)

        self.db.commit()
        return True

    def _plan_for_price(self, item: Dict[str, Any]) -> Optional[str]:
        price_id = (item.get('price') or {}).get('id')
        for plan_id, plan in self.PLANS.items():
            if price_id and plan['stripe_price_id'] == price_id:
                return plan_id
        return None

    def mark_subscription_status(self, stripe_subscription_id: Optional[str], status: str) -> bool:
        row = (
            self.db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
            .first()
        )
        if row is None:
            return False
        row.status = status
        self.db.commit()
        return True

    def cancel_subscription(self, user_id: int) -> bool:
        """Stop renewal. Access continues to the end of the paid period, and the
        customer.subscription.deleted webhook ends it then."""
        subscription = self.get_user_subscription(user_id)
        if not subscription or not subscription.stripe_subscription_id:
            return False
        if not settings.STRIPE_SECRET_KEY:
            raise BillingNotConfigured()

        stripe.Subscription.modify(
            subscription.stripe_subscription_id, cancel_at_period_end=True
        )
        subscription.cancel_at_period_end = True
        self.db.commit()
        return True

    def get_billing_portal_url(self, user_id: int, return_url: str) -> Optional[str]:
        subscription = self.get_user_subscription(user_id)
        if not subscription or not subscription.stripe_subscription_id:
            return None
        if not settings.STRIPE_SECRET_KEY:
            raise BillingNotConfigured()

        customer_id = subscription.stripe_customer_id
        if not customer_id:
            customer_id = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id
            ).customer
        return stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url).url


def get_billing_manager(db: Session) -> BillingManager:
    return BillingManager(db)
