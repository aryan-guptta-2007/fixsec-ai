"""
Stripe billing integration for FixSec AI
Handles subscriptions, plan limits, and payment processing
"""
import stripe
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from db.models import User, Subscription
from config import settings

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class BillingManager:
    """Manages Stripe billing and subscription logic"""
    
    # Plan configurations - India-friendly pricing for global market domination
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
            'price': 25,  # $25/month (₹2000/month)
            'price_inr': 199,  # ₹199/month for India
            'repos_limit': 5,
            'scans_per_day': None,  # Unlimited
            'auto_fix': False,
            'scheduled_scans': False,
            'slack_alerts': False,
            'stripe_price_id': settings.STRIPE_STARTER_PRICE_ID
        },
        'pro': {
            'name': 'Professional',
            'price': 49,  # $49/month (₹4000/month)
            'price_inr': 499,  # ₹499/month for India
            'repos_limit': None,  # Unlimited
            'scans_per_day': None,  # Unlimited
            'auto_fix': True,
            'scheduled_scans': False,
            'slack_alerts': False,
            'stripe_price_id': settings.STRIPE_PRO_PRICE_ID
        },
        'team': {
            'name': 'Team',
            'price': 99,  # $99/month (₹8000/month)
            'price_inr': 999,  # ₹999/month for India
            'repos_limit': None,  # Unlimited
            'scans_per_day': None,  # Unlimited
            'auto_fix': True,
            'scheduled_scans': True,
            'slack_alerts': True,
            'stripe_price_id': settings.STRIPE_TEAM_PRICE_ID
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get user's current subscription"""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == 'active'
        ).first()
    
    def get_user_plan(self, user_id: int) -> Dict[str, Any]:
        """Get user's current plan details"""
        subscription = self.get_user_subscription(user_id)
        
        if not subscription:
            return self.PLANS['free']
        
        return self.PLANS.get(subscription.plan_id, self.PLANS['free'])
    
    def check_repo_limit(self, user_id: int, current_repos: int) -> bool:
        """Check if user can add more repositories"""
        plan = self.get_user_plan(user_id)
        repos_limit = plan['repos_limit']
        
        if repos_limit is None:  # Unlimited
            return True
        
        return current_repos < repos_limit
    
    def check_scan_limit(self, user_id: int) -> bool:
        """Check if user can perform more scans today"""
        plan = self.get_user_plan(user_id)
        scans_per_day = plan['scans_per_day']
        
        if scans_per_day is None:  # Unlimited
            return True
        
        # Count scans today
        today = datetime.utcnow().date()
        from db.models import Scan
        
        scans_today = self.db.query(Scan).join(User).filter(
            User.id == user_id,
            Scan.created_at >= today,
            Scan.created_at < today + timedelta(days=1)
        ).count()
        
        return scans_today < scans_per_day
    
    def can_use_auto_fix(self, user_id: int) -> bool:
        """Check if user can use auto-fix feature"""
        plan = self.get_user_plan(user_id)
        return plan['auto_fix']
    
    def can_use_scheduled_scans(self, user_id: int) -> bool:
        """Check if user can use scheduled scans"""
        plan = self.get_user_plan(user_id)
        return plan['scheduled_scans']
    
    def can_use_slack_alerts(self, user_id: int) -> bool:
        """Check if user can use Slack alerts"""
        plan = self.get_user_plan(user_id)
        return plan['slack_alerts']
    
    def create_checkout_session(self, user_id: int, plan_id: str, success_url: str, cancel_url: str) -> str:
        """Create Stripe checkout session for subscription"""
        if plan_id not in self.PLANS or plan_id == 'free':
            raise ValueError("Invalid plan ID")
        
        plan = self.PLANS[plan_id]
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise ValueError("User not found")
        
        try:
            checkout_session = stripe.checkout.Session.create(
                customer_email=user.email,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan['stripe_price_id'],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user_id),
                    'plan_id': plan_id
                }
            )
            
            return checkout_session.url
        
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def handle_successful_payment(self, session_id: str) -> bool:
        """Handle successful payment from Stripe webhook"""
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                user_id = int(session.metadata['user_id'])
                plan_id = session.metadata['plan_id']
                
                # Create or update subscription
                subscription = self.get_user_subscription(user_id)
                
                if subscription:
                    # Update existing subscription
                    subscription.plan_id = plan_id
                    subscription.stripe_subscription_id = session.subscription
                    subscription.status = 'active'
                    subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
                else:
                    # Create new subscription
                    subscription = Subscription(
                        user_id=user_id,
                        plan_id=plan_id,
                        stripe_subscription_id=session.subscription,
                        status='active',
                        current_period_start=datetime.utcnow(),
                        current_period_end=datetime.utcnow() + timedelta(days=30)
                    )
                    self.db.add(subscription)
                
                self.db.commit()
                return True
        
        except Exception as e:
            print(f"Error handling successful payment: {e}")
            return False
        
        return False
    
    def cancel_subscription(self, user_id: int) -> bool:
        """Cancel user's subscription"""
        subscription = self.get_user_subscription(user_id)
        
        if not subscription or not subscription.stripe_subscription_id:
            return False
        
        try:
            # Cancel in Stripe
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Update local record
            subscription.status = 'canceled'
            self.db.commit()
            
            return True
        
        except stripe.error.StripeError as e:
            print(f"Error canceling subscription: {e}")
            return False
    
    def get_billing_portal_url(self, user_id: int, return_url: str) -> Optional[str]:
        """Create Stripe customer portal session"""
        subscription = self.get_user_subscription(user_id)
        
        if not subscription or not subscription.stripe_subscription_id:
            return None
        
        try:
            # Get customer ID from subscription
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            customer_id = stripe_subscription.customer
            
            # Create portal session
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            
            return portal_session.url
        
        except stripe.error.StripeError as e:
            print(f"Error creating portal session: {e}")
            return None

def get_billing_manager(db: Session) -> BillingManager:
    """Factory function to create BillingManager instance"""
    return BillingManager(db)