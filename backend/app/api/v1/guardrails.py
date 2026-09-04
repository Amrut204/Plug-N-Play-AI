from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.services.guardrails.compiler import AIGuardrailCompiler

router = APIRouter(prefix="/guardrails", tags=["AI Guardrails & Compliance"])


class CompileGuardrailsRequest(BaseModel):
    guidelines: str = Field(..., description="Plain English restrictions from the client")
    table_schemas: Optional[List[str]] = Field(default=None, description="Discovered tables/columns")
    doc_titles: Optional[List[str]] = Field(default=None, description="Ingested document titles")


class CompileGuardrailsResponse(BaseModel):
    banned_intents: List[str]
    restricted_columns: List[str]
    row_level_security: Dict[str, Any]
    refusal_instructions: List[str]
    refusal_message: str
    raw_guidelines: str


@router.post("/compile", response_model=CompileGuardrailsResponse, status_code=status.HTTP_200_OK)
async def compile_guardrail_policy(payload: CompileGuardrailsRequest):
    """
    Analyzes natural language business guidelines and automatically compiles
    a structured, persistent guardrail security policy.
    """
    if not payload.guidelines or not payload.guidelines.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide restriction guidelines to compile."
        )

    config = await AIGuardrailCompiler.compile_guidelines(
        guidelines=payload.guidelines,
        table_schemas=payload.table_schemas,
        doc_titles=payload.doc_titles
    )
    return config


class SuggestIndustryRulesRequest(BaseModel):
    product_description: Optional[str] = Field(default=None, description="Plain English description of the client app")
    industry_preset: Optional[str] = Field(default=None, description="Optional preset key: ecommerce, college_erp, healthcare, saas, fintech, realestate")


@router.post("/suggest-industry-rules", status_code=status.HTTP_200_OK)
async def suggest_industry_rules(payload: SuggestIndustryRulesRequest):
    """
    Performs domain threat modeling based on product description or industry preset,
    returning proactive safety recommendations.
    """
    suggestions = await AIGuardrailCompiler.suggest_industry_rules(
        product_description=payload.product_description or "",
        industry_preset=payload.industry_preset
    )
    return suggestions


@router.get("/audience-presets", status_code=status.HTTP_200_OK)
async def get_audience_presets():
    """
    Returns available target audience personas and pre-configured role boundaries.
    """
    return list(AIGuardrailCompiler.AUDIENCE_PRESETS.values())


@router.get("/industry-playbooks", status_code=status.HTTP_200_OK)
async def get_industry_playbooks():
    """
    Returns the comprehensive industry safety matrix (RAG & SQL Should / Should-Not boundaries).
    """
    return list(AIGuardrailCompiler.INDUSTRY_PRESETS.values())

