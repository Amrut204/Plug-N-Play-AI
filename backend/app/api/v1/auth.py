import re
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    generate_api_key,
    hash_api_key,
    create_access_token,
    decode_session_token,
    get_password_hash,
    verify_password
)
from app.models.tenants import Tenant, ApiKey
from app.models.agents import Agent
from app.schemas.tenants import TenantCreate, TenantResponse, ApiKeyCreate, ApiKeyResponse
from app.schemas.agents import AgentResponse
from app.services.escalation.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["Tenants & Auth"])


class ClientRegisterRequest(BaseModel):
    org_name: str = Field(..., description="Organization or project name, e.g. 'Acme Retail'")
    email: str = Field(..., description="Contact/admin email address")
    password: str = Field(..., min_length=6, description="Account password (minimum 6 characters)")
    full_name: Optional[str] = Field(default=None, description="Account holder full name")
    slug: Optional[str] = Field(default=None, description="Custom workspace slug identifier")
    otp_code: Optional[str] = Field(default=None, description="6-digit OTP verification code")
    skip_otp: Optional[bool] = Field(default=False, description="Developer flag for automated test suites")


class RegisterRequestOTP(BaseModel):
    full_name: str = Field(..., description="Account holder full name")
    org_name: str = Field(..., description="Organization or project name")
    email: str = Field(..., description="Contact/admin email address")
    password: str = Field(..., min_length=6, description="Account password (minimum 6 characters)")
    slug: Optional[str] = Field(default=None, description="Custom workspace slug identifier")


class RegisterVerifyOTP(BaseModel):
    email: str = Field(..., description="Registered account email address")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")


class ResendRegisterOTP(BaseModel):
    email: str = Field(..., description="Registered account email address")


class ClientLoginRequest(BaseModel):
    identifier: str = Field(..., description="Email address, organization slug, or project identifier")
    password: Optional[str] = Field(default=None, description="Account password")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Registered account email address")


class VerifyOTPRequest(BaseModel):
    email: str = Field(..., description="Registered account email address")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., description="Registered account email address")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    new_password: str = Field(..., min_length=6, description="New account password")


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, description="Account holder full name")
    org_name: Optional[str] = Field(default=None, description="Company or workspace name")
    email: Optional[str] = Field(default=None, description="Updated contact email")
    avatar_url: Optional[str] = Field(default=None, description="Avatar image URL")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (minimum 6 characters)")


@router.get("/smtp-diag")
async def smtp_diagnostics():
    """
    Diagnostic endpoint to test outbound SMTP connectivity from the server host.
    """
    import socket
    import smtplib

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    passwd = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM")

    results = {
        "env_vars": {
            "SMTP_HOST": host,
            "SMTP_PORT": port,
            "SMTP_USER_SET": bool(user),
            "SMTP_USER_PREVIEW": f"{user[:3]}***@{user.split('@')[-1]}" if user and "@" in user else None,
            "SMTP_PASS_SET": bool(passwd),
            "SMTP_PASS_LEN": len(passwd) if passwd else 0,
            "SMTP_FROM": sender,
        },
        "port_tests": {},
        "auth_test": {}
    }

    # Test raw TCP connectivity to port 587
    for test_port in [587, 465, 25]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4.0)
            res = s.connect_ex((host, test_port))
            s.close()
            results["port_tests"][f"{host}:{test_port}"] = "OPEN (0)" if res == 0 else f"CLOSED/BLOCKED ({res})"
        except Exception as err:
            results["port_tests"][f"{host}:{test_port}"] = f"EXCEPTION: {type(err).__name__}: {err}"

    # Test SMTP handshake and login
    if user and passwd:
        try:
            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=6.0) as server:
                    server.login(user, passwd)
                    results["auth_test"] = {"status": "success", "mode": "SSL (465)"}
            else:
                with smtplib.SMTP(host, port, timeout=6.0) as server:
                    server.starttls()
                    server.login(user, passwd)
                    results["auth_test"] = {"status": "success", "mode": "STARTTLS (587)"}
        except Exception as auth_err:
            results["auth_test"] = {
                "status": "failed",
                "error_type": type(auth_err).__name__,
                "error_detail": str(auth_err)
            }
    else:
        results["auth_test"] = {"status": "skipped", "reason": "SMTP_USER or SMTP_PASS missing in environment"}

    return results


@router.post("/register-otp", status_code=status.HTTP_200_OK)
async def request_registration_otp(payload: RegisterRequestOTP, db: AsyncSession = Depends(get_db)):
    """
    Step 1 of registration: Validates inputs, creates or updates a pending workspace (is_active=False),
    generates a 6-digit OTP code, and dispatches the verification email via SMTP.
    """
    clean_email = payload.email.strip().lower()
    clean_name = payload.org_name.strip()
    clean_full_name = payload.full_name.strip() if payload.full_name else clean_name
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    # Check if an active account already exists
    stmt_email = select(Tenant).where(Tenant.email == clean_email)
    res_email = await db.execute(stmt_email)
    existing = res_email.scalars().first()

    if existing and existing.is_active:
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists. Please sign in."
        )

    # Generate 6-digit OTP code with 10-minute expiry
    otp = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    hashed_pwd = get_password_hash(payload.password)

    if existing and not existing.is_active:
        # Re-use unverified pending tenant
        tenant = existing
        tenant.name = clean_name
        tenant.full_name = clean_full_name
        tenant.password_hash = hashed_pwd
        tenant.otp_code = otp
        tenant.otp_expires_at = expires_at
        tenant.updated_at = datetime.now(timezone.utc)
    else:
        # Generate clean slug
        slug = payload.slug
        if not slug:
            slug = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")
        if not slug:
            slug = f"org-{uuid.uuid4().hex[:6]}"

        stmt_slug = select(Tenant).where(Tenant.slug == slug)
        res_slug = await db.execute(stmt_slug)
        if res_slug.scalars().first():
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"

        tenant = Tenant(
            name=clean_name,
            slug=slug,
            email=clean_email,
            password_hash=hashed_pwd,
            full_name=clean_full_name,
            subscription_tier="free",
            is_active=False,
            otp_code=otp,
            otp_expires_at=expires_at
        )
        db.add(tenant)

    await db.commit()
    await db.refresh(tenant)

    # Dispatch verification email via EmailService
    email_result = await EmailService.send_otp_email(
        to_email=tenant.email,
        otp_code=otp,
        user_name=tenant.full_name,
        purpose="registration"
    )

    res_data = {
        "status": "success",
        "message": f"Verification code sent to {tenant.email}.",
        "email": tenant.email,
        "mode": email_result.get("mode", "smtp")
    }
    if email_result.get("mode") == "simulated":
        res_data["otp"] = otp

    return res_data


@router.post("/register-verify", status_code=status.HTTP_201_CREATED)
async def verify_registration_otp(payload: RegisterVerifyOTP, db: AsyncSession = Depends(get_db)):
    """
    Step 2 of registration: Validates the 6-digit OTP code, marks workspace as active (is_active=True),
    clears the OTP, and issues a signed JWT access token.
    """
    clean_email = payload.email.strip().lower()
    clean_otp = payload.otp_code.strip()

    stmt = select(Tenant).where(Tenant.email == clean_email)
    res = await db.execute(stmt)
    tenant = res.scalars().first()

    if not tenant or not tenant.otp_code:
        raise HTTPException(
            status_code=400,
            detail="No pending registration found for this email. Please fill in your details to create an account."
        )

    # Check expiration
    now = datetime.now(timezone.utc)
    if tenant.otp_expires_at and tenant.otp_expires_at < now:
        raise HTTPException(
            status_code=400,
            detail="Verification code has expired. Please request a new code."
        )

    if tenant.otp_code != clean_otp:
        raise HTTPException(
            status_code=400,
            detail="Incorrect verification code. Please check your email and try again."
        )

    # Activate workspace
    tenant.is_active = True
    tenant.otp_code = None
    tenant.otp_expires_at = None
    tenant.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tenant)

    token = create_access_token({
        "sub": tenant.id,
        "tenant_id": tenant.id,
        "slug": tenant.slug,
        "email": tenant.email,
        "role": "admin"
    })

    return {
        "status": "success",
        "message": "Email verified successfully! Your developer workspace is now active.",
        "token": token,
        "user": {
            "id": tenant.id,
            "full_name": tenant.full_name,
            "email": tenant.email,
            "org_name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.subscription_tier or "free"
        }
    }


@router.post("/resend-register-otp", status_code=status.HTTP_200_OK)
async def resend_registration_otp(payload: ResendRegisterOTP, db: AsyncSession = Depends(get_db)):
    """
    Resends a fresh 6-digit OTP code to an unverified registration email.
    """
    clean_email = payload.email.strip().lower()
    stmt = select(Tenant).where(Tenant.email == clean_email)
    res = await db.execute(stmt)
    tenant = res.scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="No pending account found for this email.")

    if tenant.is_active:
        return {"status": "success", "message": "Account is already verified. Please sign in."}

    otp = f"{secrets.randbelow(900000) + 100000}"
    tenant.otp_code = otp
    tenant.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    tenant.updated_at = datetime.now(timezone.utc)
    await db.commit()

    email_result = await EmailService.send_otp_email(
        to_email=tenant.email,
        otp_code=otp,
        user_name=tenant.full_name,
        purpose="registration"
    )

    res_data = {
        "status": "success",
        "message": f"Fresh verification code sent to {tenant.email}.",
        "email": tenant.email,
        "mode": email_result.get("mode", "smtp")
    }
    if email_result.get("mode") == "simulated":
        res_data["otp"] = otp

    return res_data


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_client(payload: ClientRegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Registers a new client workspace. If otp_code is provided, verifies it and activates workspace.
    If skip_otp is True, creates active workspace directly.
    Otherwise, triggers Step 1 of OTP verification.
    """
    if payload.otp_code:
        return await verify_registration_otp(
            RegisterVerifyOTP(email=payload.email, otp_code=payload.otp_code),
            db=db
        )

    if not payload.skip_otp:
        return await request_registration_otp(
            RegisterRequestOTP(
                full_name=payload.full_name or payload.org_name,
                org_name=payload.org_name,
                email=payload.email,
                password=payload.password,
                slug=payload.slug
            ),
            db=db
        )

    clean_email = payload.email.strip().lower()
    clean_name = payload.org_name.strip()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    # Check if email already registered
    stmt_email = select(Tenant).where(Tenant.email == clean_email)
    res_email = await db.execute(stmt_email)
    existing = res_email.scalars().first()
    if existing and existing.is_active:
        raise HTTPException(status_code=400, detail="An account with this email address already exists. Please sign in.")

    slug = payload.slug
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")
    if not slug:
        slug = f"org-{uuid.uuid4().hex[:6]}"

    stmt_slug = select(Tenant).where(Tenant.slug == slug)
    res_slug = await db.execute(stmt_slug)
    if res_slug.scalars().first():
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    hashed_pwd = get_password_hash(payload.password)

    if existing and not existing.is_active:
        tenant = existing
        tenant.name = clean_name
        tenant.slug = slug
        tenant.password_hash = hashed_pwd
        tenant.full_name = payload.full_name.strip() if payload.full_name else clean_name
        tenant.is_active = True
        tenant.otp_code = None
        tenant.otp_expires_at = None
    else:
        tenant = Tenant(
            name=clean_name,
            slug=slug,
            email=clean_email,
            password_hash=hashed_pwd,
            full_name=payload.full_name.strip() if payload.full_name else clean_name,
            subscription_tier="free",
            is_active=True
        )
        db.add(tenant)

    await db.commit()
    await db.refresh(tenant)

    token = create_access_token({
        "sub": tenant.id,
        "tenant_id": tenant.id,
        "slug": tenant.slug,
        "email": tenant.email,
        "role": "admin"
    })

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": tenant.id,
            "full_name": tenant.full_name,
            "email": tenant.email,
            "org_name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.subscription_tier or "free"
        }
    }


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_client(payload: ClientLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticates a client workspace by email, organization slug, or name.
    Verifies password using bcrypt if configured on the account.
    """
    ident = payload.identifier.strip().lower()

    stmt = select(Tenant).where(
        (Tenant.email == ident) | (Tenant.slug == ident) | (Tenant.name.ilike(ident))
    )
    res = await db.execute(stmt)
    tenant = res.scalars().first()

    if not tenant:
        # Demo fallback for 'default' or 'demo' in local environments
        if ident in {"default", "demo", "apex"}:
            stmt_fb = select(Tenant).limit(1)
            res_fb = await db.execute(stmt_fb)
            tenant = res_fb.scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Account or workspace not found. Please check your credentials or create a new account.")

    # Check activation status
    if tenant.is_active is False:
        raise HTTPException(
            status_code=403,
            detail="Account activation pending. Please verify your email with the 6-digit OTP code sent to your inbox."
        )

    # If account has password set, verify it
    if tenant.password_hash:
        if not payload.password:
            raise HTTPException(status_code=401, detail="Password is required for this workspace account.")
        if not verify_password(payload.password, tenant.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect password. Please try again or use 'Forgot Password' to reset.")

    # Fetch agents for this tenant
    stmt_agents = select(Agent).where(Agent.tenant_id == tenant.id)
    res_agents = await db.execute(stmt_agents)
    agents = res_agents.scalars().all()

    token = create_access_token({
        "sub": tenant.id,
        "tenant_id": tenant.id,
        "slug": tenant.slug,
        "email": tenant.email or "",
        "role": "admin"
    })

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": tenant.id,
            "full_name": tenant.full_name or tenant.name,
            "email": tenant.email,
            "org_name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.subscription_tier or "free"
        },
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "model_provider": a.model_provider,
                "model_name": a.model_name
            }
            for a in agents
        ]
    }


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Generates a secure 6-digit OTP, saves it with a 10-minute expiry,
    and sends the styled verification email via SMTP.
    """
    clean_email = payload.email.strip().lower()
    stmt = select(Tenant).where(Tenant.email == clean_email)
    res = await db.execute(stmt)
    tenant = res.scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="No account found with this email address. Please check your email or register.")

    # Generate high-entropy 6-digit numeric OTP
    otp = f"{secrets.randbelow(900000) + 100000}"
    tenant.otp_code = otp
    tenant.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.commit()

    # Dispatch email via EmailService (Gmail SMTP)
    email_result = await EmailService.send_otp_email(
        to_email=tenant.email,
        otp_code=otp,
        user_name=tenant.full_name or tenant.name
    )

    res_data = {
        "status": "success",
        "message": f"Verification code sent to {tenant.email}.",
        "email": tenant.email,
        "mode": email_result.get("mode", "smtp")
    }
    if email_result.get("mode") == "simulated":
        res_data["otp"] = otp

    return res_data


@router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(payload: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Validates the 6-digit OTP code before proceeding to password entry.
    """
    clean_email = payload.email.strip().lower()
    clean_otp = payload.otp_code.strip()

    stmt = select(Tenant).where(Tenant.email == clean_email)
    res = await db.execute(stmt)
    tenant = res.scalars().first()

    if not tenant or not tenant.otp_code:
        raise HTTPException(status_code=400, detail="Invalid verification request. Please request a new code.")

    # Check expiration
    now = datetime.now(timezone.utc)
    if tenant.otp_expires_at and tenant.otp_expires_at < now:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    if tenant.otp_code != clean_otp:
        raise HTTPException(status_code=400, detail="Incorrect verification code. Please check your email and try again.")

    return {
        "status": "success",
        "message": "Verification code confirmed."
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Verifies the 6-digit OTP and sets the new password using bcrypt.
    Clears the OTP and returns a fresh JWT access token.
    """
    clean_email = payload.email.strip().lower()
    clean_otp = payload.otp_code.strip()

    stmt = select(Tenant).where(Tenant.email == clean_email)
    res = await db.execute(stmt)
    tenant = res.scalars().first()

    if not tenant or not tenant.otp_code:
        raise HTTPException(status_code=400, detail="Invalid reset request. Please request a new code.")

    now = datetime.now(timezone.utc)
    if tenant.otp_expires_at and tenant.otp_expires_at < now:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    if tenant.otp_code != clean_otp:
        raise HTTPException(status_code=400, detail="Incorrect verification code. Please check your email.")

    # Hash new password and clear OTP
    tenant.password_hash = get_password_hash(payload.new_password)
    tenant.otp_code = None
    tenant.otp_expires_at = None
    await db.commit()
    await db.refresh(tenant)

    # Dispatch security alert
    await EmailService.send_password_changed_notification(
        to_email=tenant.email,
        user_name=tenant.full_name or tenant.name
    )

    token = create_access_token({
        "sub": tenant.id,
        "tenant_id": tenant.id,
        "slug": tenant.slug,
        "email": tenant.email,
        "role": "admin"
    })

    return {
        "status": "success",
        "message": "Password updated successfully. You are now logged in.",
        "token": token,
        "user": {
            "id": tenant.id,
            "full_name": tenant.full_name or tenant.name,
            "email": tenant.email,
            "org_name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.subscription_tier or "free"
        }
    }


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_workspace(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Validates client JWT token and returns current workspace and profile details.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization[7:]
    payload = decode_session_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired or invalid token.")

    tenant_id = payload.get("tenant_id") or payload.get("sub")
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    stmt_agents = select(Agent).where(Agent.tenant_id == tenant.id)
    res_agents = await db.execute(stmt_agents)
    agents = res_agents.scalars().all()

    return {
        "status": "success",
        "user": {
            "id": tenant.id,
            "full_name": tenant.full_name or tenant.name,
            "email": tenant.email,
            "org_name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.subscription_tier or "free",
            "avatar_url": tenant.avatar_url
        },
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "subscription_tier": tenant.subscription_tier or "free",
            "queries_used": tenant.queries_used_this_month or 0,
            "monthly_limit": tenant.monthly_query_limit or 150
        },
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "model_provider": a.model_provider,
                "model_name": a.model_name
            }
            for a in agents
        ]
    }


@router.put("/profile", status_code=status.HTTP_200_OK)
async def update_profile(
    payload: ProfileUpdateRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates user profile details: Full Name, Company Name, Email, or Avatar.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization[7:]
    token_payload = decode_session_token(token)
    if not token_payload:
        raise HTTPException(status_code=401, detail="Session expired.")

    tenant_id = token_payload.get("tenant_id") or token_payload.get("sub")
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Account not found.")

    if payload.full_name is not None and payload.full_name.strip():
        tenant.full_name = payload.full_name.strip()

    if payload.org_name is not None and payload.org_name.strip():
        tenant.name = payload.org_name.strip()

    if payload.email is not None and payload.email.strip():
        new_email = payload.email.strip().lower()
        if new_email != tenant.email:
            stmt_dup = select(Tenant).where(Tenant.email == new_email, Tenant.id != tenant.id)
            res_dup = await db.execute(stmt_dup)
            if res_dup.scalars().first():
                raise HTTPException(status_code=400, detail="This email is already registered to another account.")
            tenant.email = new_email

    if payload.avatar_url is not None:
        tenant.avatar_url = payload.avatar_url.strip()

    tenant.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tenant)

    return {
        "status": "success",
        "message": "Profile updated successfully.",
        "user": {
            "id": tenant.id,
            "full_name": tenant.full_name,
            "email": tenant.email,
            "org_name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.subscription_tier or "free",
            "avatar_url": tenant.avatar_url
        }
    }


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: ChangePasswordRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Changes user password after verifying the current password.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization[7:]
    token_payload = decode_session_token(token)
    if not token_payload:
        raise HTTPException(status_code=401, detail="Session expired.")

    tenant_id = token_payload.get("tenant_id") or token_payload.get("sub")
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Account not found.")

    if tenant.password_hash:
        if not verify_password(payload.current_password, tenant.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect.")

    tenant.password_hash = get_password_hash(payload.new_password)
    tenant.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Security email alert
    if tenant.email:
        await EmailService.send_password_changed_notification(
            to_email=tenant.email,
            user_name=tenant.full_name or tenant.name
        )

    return {
        "status": "success",
        "message": "Password changed successfully."
    }


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(payload: TenantCreate, db: AsyncSession = Depends(get_db)):
    """Create a new tenant organization."""
    stmt = select(Tenant).where(Tenant.slug == payload.slug)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Tenant with this slug already exists.")

    tenant = Tenant(name=payload.name, slug=payload.slug)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.post("/tenants/{tenant_id}/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(tenant_id: str, payload: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    """Create a secure API key for a tenant."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    api_key_record = ApiKey(
        tenant_id=tenant_id,
        name=payload.name,
        role=payload.role,
        key_hash=key_hash
    )
    db.add(api_key_record)
    await db.commit()
    await db.refresh(api_key_record)

    return ApiKeyResponse(
        id=api_key_record.id,
        name=api_key_record.name,
        role=api_key_record.role,
        api_key=raw_key,
        created_at=api_key_record.created_at
    )


@router.get("/tenants/{tenant_id}/api-keys")
async def list_api_keys(tenant_id: str, db: AsyncSession = Depends(get_db)):
    """List API keys for a tenant."""
    stmt = select(ApiKey).where(ApiKey.tenant_id == tenant_id).order_by(ApiKey.created_at.desc())
    result = await db.execute(stmt)
    keys = result.scalars().all()
    if not keys:
        # Auto-provision a default API key if none exists
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        new_key = ApiKey(tenant_id=tenant_id, name="Default Master Key", role="admin", key_hash=key_hash)
        db.add(new_key)
        await db.commit()
        await db.refresh(new_key)
        return [{
            "id": new_key.id,
            "name": new_key.name,
            "role": new_key.role,
            "api_key": raw_key,
            "created_at": new_key.created_at.isoformat() if new_key.created_at else None
        }]

    return [
        {
            "id": k.id,
            "name": k.name,
            "role": k.role,
            "api_key": f"pnp_live_{k.id[:8]}...{k.id[-4:]}",
            "created_at": k.created_at.isoformat() if k.created_at else None
        }
        for k in keys
    ]
