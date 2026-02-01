# 💰 FixSec AI Billing Setup Guide

## 🎯 Overview

This guide will help you set up Stripe billing to monetize your FixSec AI SaaS platform. With billing enabled, you can charge users for premium features and generate recurring revenue.

## 📋 Plan Structure

### Free Plan
- **Price**: $0/month
- **Repositories**: 1
- **Scans per day**: 1
- **Auto-fix PRs**: ❌
- **Scheduled scans**: ❌
- **Slack alerts**: ❌

### Professional Plan
- **Price**: $49/month
- **Repositories**: Unlimited
- **Scans per day**: Unlimited
- **Auto-fix PRs**: ✅
- **Scheduled scans**: ❌
- **Slack alerts**: ❌

### Team Plan
- **Price**: $99/month
- **Repositories**: Unlimited
- **Scans per day**: Unlimited
- **Auto-fix PRs**: ✅
- **Scheduled scans**: ✅
- **Slack alerts**: ✅

## 🔧 Stripe Setup

### Step 1: Create Stripe Account

1. Go to [stripe.com](https://stripe.com) and create an account
2. Complete business verification
3. Enable live payments

### Step 2: Create Products and Prices

1. **Go to Stripe Dashboard → Products**

2. **Create Professional Plan:**
   - Name: "FixSec AI Professional"
   - Description: "Unlimited scans and auto-fix PRs for professional developers"
   - Pricing: $49/month recurring
   - Copy the Price ID (starts with `price_`)

3. **Create Team Plan:**
   - Name: "FixSec AI Team"
   - Description: "Full-featured security platform with scheduled scans and team alerts"
   - Pricing: $99/month recurring
   - Copy the Price ID (starts with `price_`)

### Step 3: Get API Keys

1. **Go to Stripe Dashboard → Developers → API Keys**

2. **Copy these keys:**
   - **Publishable key** (starts with `pk_live_` or `pk_test_`)
   - **Secret key** (starts with `sk_live_` or `sk_test_`)

### Step 4: Set Up Webhooks

1. **Go to Stripe Dashboard → Developers → Webhooks**

2. **Create endpoint:**
   - URL: `https://your-backend-domain.com/billing/webhook`
   - Events to send:
     - `checkout.session.completed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_failed`

3. **Copy the webhook secret** (starts with `whsec_`)

## 🔐 Environment Configuration

Add these variables to your `.env.production` file:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_live_your_publishable_key_here
STRIPE_SECRET_KEY=sk_live_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Stripe Price IDs
STRIPE_PRO_PRICE_ID=price_your_pro_price_id_here
STRIPE_TEAM_PRICE_ID=price_your_team_price_id_here
```

## 🚀 Deployment

### Railway Environment Variables

Add these to your Railway deployment:

```
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_TEAM_PRICE_ID=price_...
```

### Database Migration

Run the billing migration:

```bash
# In your backend directory
python -m alembic upgrade head
```

## 🧪 Testing

### Test Mode Setup

1. **Use Stripe test keys** (start with `pk_test_` and `sk_test_`)
2. **Test card numbers:**
   - Success: `4242 4242 4242 4242`
   - Declined: `4000 0000 0000 0002`
   - Requires authentication: `4000 0025 0000 3155`

### Test Flow

1. **Visit your app** → `/billing`
2. **Click "Upgrade to Pro"**
3. **Complete checkout** with test card
4. **Verify subscription** is created in Stripe Dashboard
5. **Test premium features** (unlimited scans, auto-fix)

## 💡 Features Enabled by Billing

### Scan Limits
- **Free users**: 1 scan per day
- **Pro/Team users**: Unlimited scans
- **Enforcement**: API returns 402 status when limit exceeded

### Auto-Fix PRs
- **Free users**: Feature disabled
- **Pro/Team users**: Can create auto-fix PRs
- **Enforcement**: API returns 402 status for free users

### Scheduled Scans
- **Free/Pro users**: Feature disabled
- **Team users**: Can schedule automated scans
- **Enforcement**: UI shows upgrade prompt

### Repository Limits
- **Free users**: 1 repository
- **Pro/Team users**: Unlimited repositories
- **Enforcement**: UI prevents adding more repos

## 📊 Revenue Tracking

### Stripe Dashboard

Monitor your revenue in Stripe Dashboard:
- **Revenue**: Track monthly recurring revenue (MRR)
- **Customers**: See active subscriptions
- **Churn**: Monitor cancellation rates
- **Growth**: Track new subscriptions

### Key Metrics

- **Monthly Recurring Revenue (MRR)**
- **Customer Acquisition Cost (CAC)**
- **Lifetime Value (LTV)**
- **Churn Rate**
- **Conversion Rate** (Free → Paid)

## 🔄 Subscription Management

### Customer Portal

Users can manage their subscriptions via Stripe Customer Portal:
- **Update payment methods**
- **Download invoices**
- **Cancel subscriptions**
- **View billing history**

### Webhooks Handling

Your app automatically handles:
- **Successful payments** → Activate subscription
- **Failed payments** → Send notifications
- **Cancellations** → Downgrade to free plan
- **Updates** → Sync plan changes

## 💰 Pricing Strategy

### Market Positioning

Your pricing vs competitors:
- **Snyk**: $500-1000/month
- **Veracode**: $800-1500/month
- **Checkmarx**: $1000-2000/month
- **FixSec AI**: $49-99/month (10x cheaper!)

### Revenue Projections

**Conservative Growth:**
- Month 1: 10 customers × $49 = $490/month
- Month 6: 100 customers × $74 avg = $7,400/month
- Year 1: 500 customers × $74 avg = $37,000/month

**Aggressive Growth:**
- Month 1: 25 customers × $49 = $1,225/month
- Month 6: 300 customers × $74 avg = $22,200/month
- Year 1: 1,500 customers × $74 avg = $111,000/month

## 🎯 Conversion Optimization

### Free Trial Strategy

1. **Generous free tier** → Let users experience value
2. **Clear upgrade prompts** → Show benefits when limits hit
3. **Feature previews** → Tease premium features
4. **Social proof** → Show enterprise-grade security

### Upgrade Triggers

- **Scan limit reached** → "Upgrade for unlimited scans"
- **Multiple repos** → "Upgrade to scan all your repositories"
- **Auto-fix needed** → "Upgrade to automatically fix vulnerabilities"
- **Team features** → "Upgrade for scheduled scans and alerts"

## 🛡️ Security Best Practices

### API Keys
- **Never commit** Stripe keys to git
- **Use environment variables** for all secrets
- **Rotate keys** regularly
- **Use test keys** in development

### Webhooks
- **Verify signatures** to prevent fraud
- **Handle idempotency** for duplicate events
- **Log all events** for debugging
- **Implement retry logic** for failures

## 📈 Growth Strategies

### Customer Acquisition

1. **Product Hunt launch** → Get initial users
2. **Developer communities** → Reddit, HackerNews, Dev.to
3. **Content marketing** → Security blogs, tutorials
4. **SEO optimization** → Rank for security keywords
5. **Partnership program** → Integrate with dev tools

### Retention Strategies

1. **Onboarding flow** → Guide users to first value
2. **Regular scans** → Keep users engaged
3. **Security reports** → Show ongoing value
4. **Feature updates** → Continuous improvement
5. **Customer support** → Responsive help

## 🚨 Common Issues & Solutions

### Issue: Webhook not receiving events
**Solution**: Check webhook URL is publicly accessible and returns 200

### Issue: Subscription not activating
**Solution**: Verify webhook signature and event handling logic

### Issue: Users can't upgrade
**Solution**: Check Stripe keys and price IDs are correct

### Issue: Free users accessing premium features
**Solution**: Verify billing checks in all API endpoints

## 🎉 Launch Checklist

### Pre-Launch
- [ ] Stripe account verified and live payments enabled
- [ ] Products and prices created in Stripe
- [ ] Webhook endpoint configured and tested
- [ ] Environment variables set in production
- [ ] Database migration completed
- [ ] Billing flow tested end-to-end

### Launch Day
- [ ] Monitor webhook events in Stripe Dashboard
- [ ] Check subscription creation and activation
- [ ] Verify premium features work correctly
- [ ] Monitor error rates and user feedback
- [ ] Track conversion rates and revenue

### Post-Launch
- [ ] Set up revenue monitoring and alerts
- [ ] Analyze user behavior and conversion funnels
- [ ] Optimize pricing based on data
- [ ] Plan feature roadmap based on feedback
- [ ] Scale infrastructure as needed

## 💡 Pro Tips

### Pricing Psychology
- **Anchor high** → Show enterprise competitor pricing
- **Value-based** → Price based on value delivered, not cost
- **Simple tiers** → 3 plans maximum for clarity
- **Annual discounts** → Encourage longer commitments

### Feature Gating
- **Progressive disclosure** → Show features as users need them
- **Soft limits** → Allow occasional overages with upgrade prompts
- **Feature previews** → Let users see what they're missing
- **Usage analytics** → Track which features drive upgrades

## 🎯 Success Metrics

### Financial KPIs
- **Monthly Recurring Revenue (MRR)**: Target $10k+ by month 6
- **Annual Recurring Revenue (ARR)**: Target $100k+ by year 1
- **Customer Acquisition Cost (CAC)**: Keep under $50
- **Lifetime Value (LTV)**: Target 3:1 LTV:CAC ratio

### Product KPIs
- **Free to Paid Conversion**: Target 5-10%
- **Churn Rate**: Keep monthly churn under 5%
- **Feature Adoption**: Track premium feature usage
- **User Engagement**: Monitor scan frequency and retention

---

## 🎉 You're Ready to Make Money!

With billing set up, your FixSec AI platform can now:
- ✅ **Generate recurring revenue** from subscriptions
- ✅ **Enforce plan limits** to encourage upgrades
- ✅ **Scale automatically** with Stripe infrastructure
- ✅ **Compete with enterprise tools** at 10x lower price

**Your security SaaS is now a complete, revenue-generating business!** 💰🚀

---

## 📞 Support

- **Stripe Documentation**: [stripe.com/docs](https://stripe.com/docs)
- **Webhook Testing**: [webhook.site](https://webhook.site)
- **Test Cards**: [stripe.com/docs/testing](https://stripe.com/docs/testing)

**Ready to launch your profitable security SaaS? Let's make it happen!** 🎯💪