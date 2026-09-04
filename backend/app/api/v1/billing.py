import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.models.tenants import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing & Subscriptions"])

# =========================================================================
# PLAN MATRIX CONFIGURATION
# =========================================================================
PLAN_SPECS = {
    "free": {
        "name": "Free Explorer",
        "tagline": "Best for hobbyists & testing",
        "monthly_query_limit": 150,
        "max_bots": 1,
        "pricing": {
            "USD": {"monthly": 0, "annual": 0, "annual_monthly_equiv": 0},
            "INR": {"monthly": 0, "annual": 0, "annual_monthly_equiv": 0}
        },
        "features": [
            "150 queries / month (Refreshes monthly)",
            "1 Active AI Assistant Bot",
            "Document Knowledge RAG (5 docs / 2MB)",
            "1 SQL Database connection",
            "All 7 Framework Widgets",
            "Starter Quick Questions (Prompt Chips)",
            "7-day analytics & audit logs",
            "Community Support"
        ]
    },
    "starter": {
        "name": "Starter",
        "tagline": "Best for small websites & stores",
        "monthly_query_limit": 1500,
        "max_bots": 2,
        "pricing": {
            "USD": {"monthly": 29, "annual": 290, "annual_monthly_equiv": 24.16},
            "INR": {"monthly": 2499, "annual": 24990, "annual_monthly_equiv": 2082.50}
        },
        "features": [
            "1,500 queries / month",
            "2 Active AI Assistant Bots",
            "25 Knowledge Base Documents",
            "1 SQL Database connection",
            "White-label (Remove 'Powered by' badge)",
            "30-day log history & analytics",
            "Email Support (24h SLA)",
            "All 7 Framework Widgets"
        ]
    },
    "pro": {
        "name": "Pro / Growth",
        "tagline": "Best for growing SaaS, clinics & colleges",
        "monthly_query_limit": 8000,
        "max_bots": 5,
        "pricing": {
            "USD": {"monthly": 99, "annual": 990, "annual_monthly_equiv": 82.50},
            "INR": {"monthly": 7999, "annual": 79990, "annual_monthly_equiv": 6665.83}
        },
        "features": [
            "8,000 queries / month",
            "5 Active AI Assistant Bots",
            "Unlimited Documents & Knowledge Base",
            "Up to 3 SQL Databases",
            "Zero-Knowledge Private VPC Bridge",
            "Speech-to-Text & Voice TTS output",
            "Human Support Escalation (Slack/Email)",
            "Priority Support (4h SLA)"
        ]
    },
    "business": {
        "name": "Business",
        "tagline": "Best for multi-branch & large apps",
        "monthly_query_limit": 30000,
        "max_bots": 15,
        "pricing": {
            "USD": {"monthly": 299, "annual": 2990, "annual_monthly_equiv": 249.16},
            "INR": {"monthly": 24999, "annual": 249990, "annual_monthly_equiv": 20832.50}
        },
        "features": [
            "30,000 queries / month",
            "15 Active AI Assistant Bots",
            "Multi-Database Query Federation",
            "Custom AI Guardrail Policy Compiler",
            "Custom Domain Whitelisting",
            "90-day comprehensive audit logs",
            "99.9% Uptime SLA Guarantee",
            "Dedicated Account Manager"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "tagline": "Best for banks, hospitals & institutions",
        "monthly_query_limit": 100000,
        "max_bots": 999,
        "pricing": {
            "USD": {"monthly": "Custom", "annual": "Custom", "annual_monthly_equiv": "Custom"},
            "INR": {"monthly": "Custom", "annual": "Custom", "annual_monthly_equiv": "Custom"}
        },
        "features": [
            "100k+ to Unlimited queries",
            "Unlimited Active AI Bots",
            "Self-Hosted / On-Premise Docker",
            "Private VPC / Air-Gapped Setup",
            "Custom LLM Fine-Tuning & vLLM",
            "Dedicated Support Engineer",
            "Custom NDA, BAA & SOC2 Compliance"
        ]
    }
}


# =========================================================================
# SCHEMAS
# =========================================================================
class CheckoutSessionRequest(BaseModel):
    tenant_id: str
    plan_tier: str = Field(..., description="Plan tier: 'free', 'starter', 'pro', 'business', 'enterprise'")
    billing_cycle: str = Field(default="monthly", description="'monthly' or 'annual'")
    currency: str = Field(default="USD", description="'USD' or 'INR'")
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class ChangePlanRequest(BaseModel):
    tenant_id: str
    plan_tier: str = Field(..., description="'free', 'starter', 'pro', 'business', 'enterprise'")
    billing_cycle: str = Field(default="monthly", description="'monthly' or 'annual'")
    currency: str = Field(default="USD", description="'USD' or 'INR'")


# =========================================================================
# ENDPOINTS
# =========================================================================
@router.get("/plans", status_code=status.HTTP_200_OK)
async def get_plans_matrix():
    """Returns available subscription tiers, pricing in USD and INR, and feature limits."""
    return {"plans": PLAN_SPECS}


@router.get("/usage", status_code=status.HTTP_200_OK)
async def get_tenant_usage(tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Returns current query usage, remaining quota, active plan details, and reset countdown."""
    if not tenant_id:
        stmt = select(Tenant).where(Tenant.is_active == True).order_by(Tenant.created_at.asc())
        res = await db.execute(stmt)
        tenant = res.scalars().first()
    else:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        res = await db.execute(stmt)
        tenant = res.scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    tier = tenant.subscription_tier or "free"
    plan_info = PLAN_SPECS.get(tier, PLAN_SPECS["free"])
    limit = tenant.monthly_query_limit or plan_info["monthly_query_limit"]
    used = tenant.queries_used_this_month or 0
    remaining = max(0, limit - used)
    pct_used = min(100.0, round((used / max(1, limit)) * 100, 1))

    # Calculate days left in billing cycle (assumes 30 days cycle)
    now = datetime.now(timezone.utc)
    if tenant.subscription_period_end:
        period_end = tenant.subscription_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        days_left = max(0, (period_end - now).days)
    else:
        # Default 30 day cycle from created_at
        created = tenant.created_at or now
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        cycle_day = (now - created).days % 30
        days_left = max(1, 30 - cycle_day)

    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "subscription_tier": tier,
        "tier_name": plan_info["name"],
        "billing_cycle": tenant.billing_cycle or "monthly",
        "currency": tenant.billing_currency or "USD",
        "monthly_query_limit": limit,
        "queries_used_this_month": used,
        "queries_remaining": remaining,
        "percent_used": pct_used,
        "days_until_reset": days_left,
        "subscription_status": tenant.subscription_status or "active",
        "plan_features": plan_info["features"],
        "max_bots": plan_info["max_bots"]
    }


@router.post("/create-checkout-session", status_code=status.HTTP_200_OK)
async def create_checkout_session(payload: CheckoutSessionRequest, db: AsyncSession = Depends(get_db)):
    """
    Creates a Stripe Checkout Session for plan upgrades.
    Supports instant fallback simulation for testing environments.
    """
    stmt = select(Tenant).where(Tenant.id == payload.tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    plan_info = PLAN_SPECS.get(payload.plan_tier)
    if not plan_info:
        raise HTTPException(status_code=400, detail=f"Invalid plan tier '{payload.plan_tier}'.")

    # Seamless switch back to Free tier
    if payload.plan_tier == "free":
        tenant.subscription_tier = "free"
        tenant.monthly_query_limit = plan_info["monthly_query_limit"]
        tenant.subscription_status = "active"
        tenant.subscription_period_end = None
        await db.commit()
        return {
            "checkout_url": "http://127.0.0.1:8000/?billing_plan=free",
            "session_id": f"free_{tenant.id}",
            "mode": "simulated",
            "message": "Switched to Free Explorer plan (150 queries/month) successfully!",
            "new_limit": plan_info["monthly_query_limit"],
            "plan_tier": "free"
        }

    # Enterprise tier requires custom deployment
    if payload.plan_tier == "enterprise":
        return {
            "checkout_url": None,
            "session_id": None,
            "mode": "contact_sales",
            "message": "Enterprise tier requires dedicated setup. Please contact sales at enterprise@plugnplay-ai.com.",
            "new_limit": plan_info["monthly_query_limit"],
            "plan_tier": "enterprise"
        }

    curr = payload.currency.upper() if payload.currency.upper() in ["USD", "INR"] else "USD"
    cycle = payload.billing_cycle.lower() if payload.billing_cycle.lower() in ["monthly", "annual"] else "monthly"
    price = plan_info["pricing"][curr][cycle]

    stripe_api_key = os.getenv("STRIPE_SECRET_KEY", "")
    
    # If Stripe key is present, create real Stripe Session
    if stripe_api_key:
        try:
            import stripe
            stripe.api_key = stripe_api_key
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": curr.lower(),
                        "product_data": {
                            "name": f"Plug-N-Play AI - {plan_info['name']} ({cycle.capitalize()})",
                            "description": f"{plan_info['monthly_query_limit']:,} queries/mo with {plan_info['max_bots']} active bots",
                        },
                        "unit_amount": int(price * 100),
                        "recurring": {"interval": "year" if cycle == "annual" else "month"}
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=payload.success_url or "http://127.0.0.1:8000/?billing=success",
                cancel_url=payload.cancel_url or "http://127.0.0.1:8000/?billing=cancel",
                client_reference_id=tenant.id,
                metadata={
                    "tenant_id": tenant.id,
                    "plan_tier": payload.plan_tier,
                    "billing_cycle": cycle,
                    "currency": curr
                }
            )
            return {"checkout_url": session.url, "session_id": session.id, "mode": "stripe"}
        except Exception as e:
            logger.warning(f"Stripe API error: {e}. Falling back to 1-click upgrade simulation.")

    # Seamless Local/Demo Simulation Fallback
    period_end = datetime.now(timezone.utc) + timedelta(days=365 if cycle == "annual" else 30)
    tenant.subscription_tier = payload.plan_tier
    tenant.billing_cycle = cycle
    tenant.billing_currency = curr
    tenant.monthly_query_limit = plan_info["monthly_query_limit"]
    tenant.subscription_status = "active"
    tenant.subscription_period_end = period_end
    await db.commit()

    return {
        "checkout_url": f"http://127.0.0.1:8000/?billing_upgraded={payload.plan_tier}",
        "session_id": f"sim_sub_{tenant.id}_{payload.plan_tier}",
        "mode": "simulated",
        "message": f"Successfully upgraded to {plan_info['name']} ({cycle.capitalize()})!",
        "new_limit": plan_info["monthly_query_limit"]
    }


@router.post("/change-plan", status_code=status.HTTP_200_OK)
async def direct_change_plan(payload: ChangePlanRequest, db: AsyncSession = Depends(get_db)):
    """Directly update tenant plan for instant testing and manual admin management."""
    stmt = select(Tenant).where(Tenant.id == payload.tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    plan_info = PLAN_SPECS.get(payload.plan_tier)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Invalid plan tier.")

    curr = payload.currency.upper() if payload.currency.upper() in ["USD", "INR"] else "USD"
    cycle = payload.billing_cycle.lower() if payload.billing_cycle.lower() in ["monthly", "annual"] else "monthly"

    tenant.subscription_tier = payload.plan_tier
    tenant.billing_cycle = cycle
    tenant.billing_currency = curr
    tenant.monthly_query_limit = plan_info["monthly_query_limit"]
    tenant.subscription_status = "active"
    tenant.subscription_period_end = datetime.now(timezone.utc) + timedelta(days=365 if cycle == "annual" else 30)
    
    # If downgrading to free, reset used queries if desired or keep history
    await db.commit()

    return {
        "status": "success",
        "tenant_id": tenant.id,
        "subscription_tier": tenant.subscription_tier,
        "tier_name": plan_info["name"],
        "monthly_query_limit": tenant.monthly_query_limit,
        "billing_currency": tenant.billing_currency,
        "billing_cycle": tenant.billing_cycle
    }


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None, alias="stripe-signature"), db: AsyncSession = Depends(get_db)):
    """Handles Stripe webhooks to automatically upgrade or cancel tenant subscriptions."""
    payload_body = await request.body()
    stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    event = None
    if stripe_webhook_secret and stripe_signature:
        try:
            import stripe
            event = stripe.Webhook.construct_event(payload_body, stripe_signature, stripe_webhook_secret)
        except Exception as e:
            logger.error(f"Stripe webhook signature validation failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        try:
            event = json.loads(payload_body.decode('utf-8'))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})

    logger.info(f"Processing Stripe Webhook: {event_type}")

    if event_type == "checkout.session.completed":
        metadata = data_object.get("metadata", {})
        tenant_id = metadata.get("tenant_id") or data_object.get("client_reference_id")
        plan_tier = metadata.get("plan_tier")
        billing_cycle = metadata.get("billing_cycle", "monthly")
        currency = metadata.get("currency", "USD")

        if tenant_id and plan_tier and plan_tier in PLAN_SPECS:
            plan_info = PLAN_SPECS[plan_tier]
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            res = await db.execute(stmt)
            tenant = res.scalars().first()
            if tenant:
                tenant.subscription_tier = plan_tier
                tenant.billing_cycle = billing_cycle
                tenant.billing_currency = currency
                tenant.monthly_query_limit = plan_info["monthly_query_limit"]
                tenant.stripe_customer_id = data_object.get("customer")
                tenant.stripe_subscription_id = data_object.get("subscription")
                tenant.subscription_status = "active"
                await db.commit()
                logger.info(f"Tenant {tenant_id} upgraded to {plan_tier} via Stripe Webhook.")

    elif event_type in ["customer.subscription.deleted", "customer.subscription.canceled"]:
        sub_id = data_object.get("id")
        if sub_id:
            stmt = select(Tenant).where(Tenant.stripe_subscription_id == sub_id)
            res = await db.execute(stmt)
            tenant = res.scalars().first()
            if tenant:
                tenant.subscription_tier = "free"
                tenant.monthly_query_limit = 150
                tenant.subscription_status = "canceled"
                await db.commit()
                logger.info(f"Tenant {tenant.id} reverted to free tier due to subscription cancellation.")

    return {"status": "received"}
