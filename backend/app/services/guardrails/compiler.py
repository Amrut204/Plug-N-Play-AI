import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.services.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


class AIGuardrailCompiler:
    """
    Intelligent Guardrail Compiler:
    Converts plain English business restriction guidelines into structured,
    deterministic security policies enforceable at:
    - Gate 1: 0-Token fast intent blocking (sub-1ms)
    - Gate 2: Database schema column pruning & row-level security
    - Gate 3: LLM system prompt anti-jailbreak directives
    """

    DEFAULT_FALLBACK_REFUSAL = (
        "I am programmed to provide official policy information only and cannot "
        "assist with requests to bypass, circumvent, or manipulate institutional rules."
    )

    INDUSTRY_PRESETS = {
        "ecommerce": {
            "key": "ecommerce",
            "industry_name": "E-Commerce & Retail Store",
            "main_goal": "Drive sales, resolve order issues, and locate product information while protecting margins and customer privacy.",
            "rag_capabilities": {
                "should_answer": [
                    "Product Specs: Materials, dimensions, weight, and compatibility.",
                    "Return Policies: Step-by-step return processes, warranty terms, and timelines.",
                    "Shipping Tracking: Order status updates and tracking timeline explanations.",
                    "Personalized Recommendations: Items based on browsing preferences or explicit requirements."
                ],
                "should_not_answer": [
                    "Competitor Comparisons: Direct, unverified trashing or bashing of rival brands.",
                    "Hidden Discounts: Negotiating custom prices outside active promotional codes.",
                    "Unverified Stock: Confidently promising item availability for low-stock inventory."
                ]
            },
            "sql_capabilities": {
                "should_answer": [
                    "Sales Trends: 'Which product category grew the most last month?'",
                    "Inventory Levels: 'List items with fewer than 10 units in stock.'",
                    "Customer Loyalty: 'Identify users who spent over $500 this quarter.'"
                ],
                "should_not_answer": [
                    "Plain-Text Passwords: Never reveal user credentials or authentication hashes.",
                    "Full Credit Cards: Never expose raw financial transaction tokens, CVVs, or card details.",
                    "Unrestricted Bulk Leaks: Block downloading or dumping the entire customer database."
                ]
            },
            "restricted_columns": ["cost_price", "wholesale_price", "profit_margin", "password_hash", "credit_card", "cvv", "stripe_token", "shipping_address_other_users"],
            "banned_intents": ["negotiate_custom_price", "trash_competitor", "download_all_customers", "leak_wholesale_margin"],
            "compiled_guidelines": "Never disclose wholesale supplier costs, profit margins, competitor smear comparisons, or payment card details. Answer product specs, return windows, and order statuses accurately."
        },
        "college_erp": {
            "key": "college_erp",
            "industry_name": "College & University ERP",
            "main_goal": "Streamline campus administration, grading, and student schedules while complying with FERPA student privacy.",
            "rag_capabilities": {
                "should_answer": [
                    "Campus Navigation: Building locations, office hours, and facility maps.",
                    "Academic Deadlines: Drop/add dates, exam schedules, and holiday calendars.",
                    "Syllabus Details: Course prerequisites, credits, and required reading materials.",
                    "Policy Clarity: Library rules, housing guidelines, and grading scales."
                ],
                "should_not_answer": [
                    "Disciplinary Actions: Discussing student behavior files, probationary notes, or suspensions.",
                    "Admission Bias: Explaining subjective internal selection committee notes or quotas.",
                    "Staff Gossip: Sharing professor personal contact numbers, private emails, or HR reviews."
                ]
            },
            "sql_capabilities": {
                "should_answer": [
                    "Class Occupancy: 'Which elective courses have remaining open seats?'",
                    "GPA Tracking: 'Calculate the average GPA of senior engineering students.'",
                    "Fee Collection: 'List students with outstanding tuition balances.'"
                ],
                "should_not_answer": [
                    "Peer Grades: Showing Student A the individual marks, grades, or transcripts of Student B.",
                    "Private Staff Data: Querying professor salary bands, compensation packages, or home addresses.",
                    "Demographic Profiling: Creating unverified lists filtered by sensitive, protected student data."
                ]
            },
            "restricted_columns": ["cgpa", "marks", "grade", "faculty_salary", "professor_phone", "disciplinary_notes", "admission_score", "ssn"],
            "banned_intents": ["view_other_student_grades", "view_faculty_salaries", "bypass_attendance_rules", "view_disciplinary_records"],
            "compiled_guidelines": "Comply strictly with FERPA student privacy. Never reveal another student's marks, grades, or GPA. Never expose faculty salaries or private disciplinary files. Assist with campus deadlines, course schedules, and occupancy."
        },
        "healthcare": {
            "key": "healthcare",
            "industry_name": "Healthcare & Clinic Management",
            "main_goal": "Triage general questions, manage appointments, and safeguard Protected Health Information (PHI/HIPAA).",
            "rag_capabilities": {
                "should_answer": [
                    "General Education: Explaining common medical terms, known drug side effects, or symptoms.",
                    "Prep Instructions: 'Do I need to fast before my fasting blood glucose test?'",
                    "Clinic Logistics: Hours of operation, insurance network verification, and facility locations.",
                    "Doctor Bios: Credentials, medical specializations, and booking availability."
                ],
                "should_not_answer": [
                    "Definitive Diagnoses: Telling a patient they definitively have a specific disease or condition.",
                    "Dosage Changes: Altering prescriptions or telling patients to stop taking prescribed meds.",
                    "Emergency Handling: Attempting to guide a patient through active chest pain, stroke symptoms, or severe trauma (direct to emergency services immediately)."
                ]
            },
            "sql_capabilities": {
                "should_answer": [
                    "Schedule Availability: 'Find open slots for Dr. Smith next Tuesday morning.'",
                    "Anonymized Analytics: 'What percentage of patients missed appointments this month?'",
                    "Billing Transparency: 'Show the itemized cost breakdown for procedure code 99213.'"
                ],
                "should_not_answer": [
                    "Identifiable Charts: Exposing Protected Health Information (PHI) without matching token authorization.",
                    "Cross-Patient Leaks: Allowing staff to see medical histories of patients not assigned to them.",
                    "Raw Lab Results: Revealing complex genetic or oncology markers before a physician reviews them with the patient."
                ]
            },
            "restricted_columns": ["phi_records", "patient_ssn", "genetic_markers", "diagnosis_history", "lab_notes_unreviewed", "billing_card_token"],
            "banned_intents": ["diagnose_critical_illness", "alter_prescription_dosage", "leak_patient_medical_history"],
            "compiled_guidelines": "Enforce strict HIPAA / PHI compliance. Do not issue definitive medical diagnoses or alter prescribed drug dosages. Direct emergencies to 911/emergency care. Anonymize patient analytics and isolate patient charts."
        },
        "saas": {
            "key": "saas",
            "industry_name": "B2B SaaS & Developer APIs",
            "main_goal": "Onboard users, troubleshoot software bugs, and clarify subscription tiers with strict multi-tenant isolation.",
            "rag_capabilities": {
                "should_answer": [
                    "API Integration: Providing code snippets, SDK examples, and troubleshooting error webhooks.",
                    "Feature Documentation: Explaining how to configure specific workspace settings and integrations.",
                    "Plan Limitations: Detailing what features are locked behind higher subscription tiers.",
                    "Service Health: Current server uptime status, maintenance windows, and incident reports."
                ],
                "should_not_answer": [
                    "Custom SLA Promises: Binding the company to legally enforceable uptime metrics in chat.",
                    "Future Roadmaps: Guaranteeing specific release dates for unbuilt product features.",
                    "Cross-Tenant Data: Discussing how another corporate client uses the software or custom configurations."
                ]
            },
            "sql_capabilities": {
                "should_answer": [
                    "Usage Metrics: 'How many API requests did Organization X make today?'",
                    "Churn Warning: 'List accounts that have not logged in for 14 days.'",
                    "MRR Calculation: 'What is the Monthly Recurring Revenue from the Enterprise plan?'"
                ],
                "should_not_answer": [
                    "Cross-Tenant Leaks: Allowing Tenant A to query rows, databases, or configs belonging to Tenant B.",
                    "Proprietary Secrets: Revealing master API keys, JWT secrets, or internal database architecture.",
                    "Raw Payment Tokens: Exposing corporate billing account numbers or banking tokens."
                ]
            },
            "restricted_columns": ["master_api_key", "jwt_secret", "database_connection_url", "stripe_customer_id", "billing_bank_account"],
            "banned_intents": ["leak_other_tenant_data", "promise_custom_sla", "reveal_master_secrets", "bypass_rate_limit"],
            "compiled_guidelines": "Enforce strict multi-tenant data boundaries (SOC 2). Never reveal master API keys, internal architecture, or cross-tenant data. Do not make legally binding SLA promises or promise unreleased roadmaps."
        },
        "fintech": {
            "key": "fintech",
            "industry_name": "FinTech & Loan Management",
            "main_goal": "Guide loan applications, calculate interest, and maintain financial compliance (PCI-DSS & Fair Lending).",
            "rag_capabilities": {
                "should_answer": [
                    "Application Checklist: Listing documents required for a mortgage, business, or personal loan.",
                    "Product Definitions: Explaining fixed vs. variable rates, APR, or amortization schedules.",
                    "Application Progress: Letting authenticated applicants know what stage their paperwork is in.",
                    "Payment Calculations: Showing hypothetical monthly costs based on standard formula inputs."
                ],
                "should_not_answer": [
                    "Guaranteed Approvals: Saying 'You are 100% approved' before formal underwriting.",
                    "Financial Planning: Telling users exactly where to invest their personal money or stocks.",
                    "Rejection Arguments: Getting into debates or making exceptions regarding a denied credit score assessment."
                ]
            },
            "sql_capabilities": {
                "should_answer": [
                    "Risk Assessment: 'What is the average credit score of our current borrowers?'",
                    "Delinquency Reporting: 'List all loans currently more than 30 days overdue.'",
                    "Portfolio Yields: 'Calculate total interest earned from auto loans this quarter.'"
                ],
                "should_not_answer": [
                    "SSN / Government IDs: Returning unencrypted social security numbers, PAN, or tax identifiers.",
                    "Credit File Tampering: Executing database modifications that manipulate a user's credit rating.",
                    "Regulatory Violations: Letting unprivileged accounts run bulk reports without compliance logging."
                ]
            },
            "restricted_columns": ["ssn", "pan_card", "bank_account_number", "routing_number", "credit_underwriting_secret_formula", "card_pin"],
            "banned_intents": ["guarantee_loan_approval", "give_investment_advice", "leak_tax_identifiers", "bypass_kyc_checks"],
            "compiled_guidelines": "Comply with PCI-DSS and Fair Lending laws. Strictly redact SSN, tax IDs, and bank account numbers. Never guarantee loan approvals before formal underwriting, and never give individual investment advice."
        },
        "realestate": {
            "key": "realestate",
            "industry_name": "Real Estate & Property Management",
            "main_goal": "Filter properties, coordinate tours, and clarify leasing parameters while following Fair Housing regulations.",
            "rag_capabilities": {
                "should_answer": [
                    "Property Attributes: Square footage, parking options, school zones, and HVAC heating/cooling types.",
                    "Lease Basics: Security deposit requirements, pet policies, HOA rules, and utility splits.",
                    "Tour Booking: Checking agent availability and scheduling property walkthroughs.",
                    "Neighborhood Stats: Proximity to public transit, grocery stores, and parks."
                ],
                "should_not_answer": [
                    "Discriminatory Bias: Commenting on neighborhood racial/religious demographics (violating Fair Housing laws).",
                    "Price Guarantees: Finalizing a lower rent or purchase price without landlord/seller consent.",
                    "Structural Hidden Flaws: Concealing known mold, asbestos, flood, or structural failures."
                ]
            },
            "sql_capabilities": {
                "should_answer": [
                    "Property Matching: 'List 3-bedroom houses under $450,000 with a pool.'",
                    "Agent Performance: 'Which real estate agent closed the highest volume this month?'",
                    "Rental Yields: 'Show average rent per square foot across city zip codes.'"
                ],
                "should_not_answer": [
                    "Owner Financial Strain: Exposing if an owner is desperate to sell due to bankruptcy or foreclosure.",
                    "Tenant Complaints: Revealing internal landlord notes about difficult tenants.",
                    "Security Codes: Giving out gate pins, lockbox keys, or security alarm codes via text queries."
                ]
            },
            "restricted_columns": ["gate_pin", "lockbox_code", "alarm_code", "owner_distress_notes", "tenant_credit_score_full", "ssn"],
            "banned_intents": ["demographic_steering_discrimination", "leak_lockbox_security_codes", "disclose_owner_distress_pricing"],
            "compiled_guidelines": "Comply with Fair Housing laws by avoiding demographic steering or discrimination. Never disclose lockbox codes, gate alarm pins, or owner distress financial notes. Answer property specs, tour booking, and leasing rules."
        }
    }

    AUDIENCE_PRESETS = {
        "end_user": {
            "key": "end_user",
            "name": "End-Users (Students / Customers / Shoppers)",
            "badge": "Strict Privacy Shield",
            "summary": "Full zero-leakage isolation. Queries limited to logged-in user's own data. Sensitive personal fields redacted.",
            "restricted_columns": ["cgpa", "marks", "grade", "phone", "email", "salary", "cost_price", "profit_margin", "address", "ssn", "password_hash"],
            "banned_intents": ["bypass_policy", "cheat_exam", "fake_certificate", "scrape_other_users", "view_all_records", "view_financial_margins"],
            "suggested_rules": "Do not reveal other users' personal records, marks, phone numbers, or internal pricing. Restrict database answers strictly to the authenticated user.",
            "row_level_security": {"enforce_user_isolation": True, "allow_aggregate_analytics": False}
        },
        "staff": {
            "key": "staff",
            "name": "Operational Staff (Teachers / TPO / Support)",
            "badge": "Department Lookup",
            "summary": "Enables batch lookup and candidate status tracking, but blocks executive compensation, master API keys, and financial ledgers.",
            "restricted_columns": ["salary", "executive_compensation", "api_key", "password_hash", "master_secret", "bank_account"],
            "banned_intents": ["view_executive_salaries", "export_system_keys", "bypass_system_auth"],
            "suggested_rules": "Allow querying student placement statuses, department rosters, and order tracking. Strictly hide executive payroll and master secrets.",
            "row_level_security": {"enforce_user_isolation": False, "allow_aggregate_analytics": True}
        },
        "management": {
            "key": "management",
            "name": "Management & Business Owners (Dean / Store Owner)",
            "badge": "Full Analytics",
            "summary": "Full cross-table analytics, revenue breakdowns, and macro reports with strict read-only assurance.",
            "restricted_columns": ["password_hash", "master_secret"],
            "banned_intents": ["destructive_database_modification"],
            "suggested_rules": "Provide full analytical reports, attendance distributions, revenue metrics, and performance comparisons.",
            "row_level_security": {"enforce_user_isolation": False, "allow_aggregate_analytics": True}
        },
        "adaptive": {
            "key": "adaptive",
            "name": "Adaptive Multi-Role (Dynamic RBAC)",
            "badge": "Dynamic Boundary",
            "summary": "Dynamically adjusts permission boundaries on every single query based on the 'user_role' (e.g. student vs admin) inside JWT session.",
            "restricted_columns": ["password_hash", "master_secret"],
            "banned_intents": ["bypass_role_permissions"],
            "suggested_rules": "Enforce dynamic role-based access control. If user_role is 'admin' or 'faculty', grant elevated access; otherwise strictly isolate user records.",
            "row_level_security": {"enforce_user_isolation": "dynamic", "allow_aggregate_analytics": "dynamic"}
        }
    }

    @classmethod
    def get_audience_preset(cls, audience_key: str) -> Dict[str, Any]:
        """Returns the guardrail profile for a specific audience persona."""
        return cls.AUDIENCE_PRESETS.get(audience_key, cls.AUDIENCE_PRESETS["end_user"])

    @classmethod
    async def suggest_industry_rules(
        cls,
        product_description: str,
        industry_preset: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes a client's product domain or industry preset and returns
        proactive threat modeling recommendations.
        """
        # If preset provided and matches
        if industry_preset and industry_preset.lower() in cls.INDUSTRY_PRESETS:
            return cls.INDUSTRY_PRESETS[industry_preset.lower()]

        # Check if description matches any preset keyword
        desc_low = (product_description or "").lower()
        if any(w in desc_low for w in ["college", "university", "school", "student", "attendance", "faculty"]):
            return cls.INDUSTRY_PRESETS["college_erp"]
        if any(w in desc_low for w in ["ecommerce", "e-commerce", "store", "shop", "product", "cart", "return", "refund"]):
            return cls.INDUSTRY_PRESETS["ecommerce"]
        if any(w in desc_low for w in ["health", "clinic", "doctor", "patient", "medical", "pharmacy", "hospital"]):
            return cls.INDUSTRY_PRESETS["healthcare"]
        if any(w in desc_low for w in ["saas", "api", "software", "developer", "cloud", "platform"]):
            return cls.INDUSTRY_PRESETS["saas"]
        if any(w in desc_low for w in ["bank", "loan", "fintech", "credit", "payment", "finance", "crypto"]):
            return cls.INDUSTRY_PRESETS["fintech"]
        if any(w in desc_low for w in ["real estate", "property", "rent", "housing", "realtor", "apartment"]):
            return cls.INDUSTRY_PRESETS["realestate"]

        # If custom description, use LLM to perform proactive threat modeling
        if not product_description or len(product_description.strip()) < 5:
            return cls.INDUSTRY_PRESETS["ecommerce"]

        system_prompt = (
            "You are an Enterprise AI Security & Compliance Threat Modeling Expert. "
            "Given a description of a client's web application, determine the industry and identify "
            "the top 3 critical things an AI chatbot on this app should NEVER reveal or do.\n"
            "Respond ONLY with valid JSON conforming to this schema:\n"
            "{\n"
            '  "industry_name": "Name of Industry",\n'
            '  "risk_summary": "1 sentence summarizing top vulnerabilities",\n'
            '  "recommended_restrictions": [\n'
            '    {\n'
            '      "id": "rule_id_string",\n'
            '      "title": "Short imperative title",\n'
            '      "description": "Specific guideline on what to block/hide",\n'
            '      "category": "data_privacy|fraud_prevention|policy_compliance|security",\n'
            '      "is_default_checked": true\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Product Description:\n\"{product_description.strip()}\""}
            ]
            response = await LLMGateway.complete(
                messages=messages,
                model="qwen/qwen3.8-27b",
                temperature=0.1,
                max_tokens=400
            )
            raw = response.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            parsed = json.loads(raw)
            return parsed
        except Exception as e:
            logger.warning(f"Custom industry threat modeling failed: {e}. Falling back to default.")
            return cls.INDUSTRY_PRESETS["ecommerce"]

    @classmethod
    async def compile_guidelines(
        cls,
        guidelines: str,
        table_schemas: Optional[List[str]] = None,
        doc_titles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes plain English guidelines into a structured Guardrail JSON configuration.
        """
        if not guidelines or not guidelines.strip():
            return cls._default_guardrail_config()

        clean_guidelines = guidelines.strip()
        context_hint = ""
        if table_schemas:
            context_hint += f"\nDatabase Tables/Fields: {', '.join(table_schemas[:10])}"
        if doc_titles:
            context_hint += f"\nKnowledge Documents: {', '.join(doc_titles[:5])}"

        system_prompt = (
            "You are an Enterprise AI Security & Compliance Guardrail Compiler.\n"
            "Convert user business restriction guidelines into a strict, compact JSON security policy.\n"
            "CRITICAL RULES:\n"
            "1. 'restricted_columns': List all exact sensitive field names to hide from AI and database queries (e.g., 'cgpa', 'gpa', 'sgpa', 'marks', 'grade', 'score', 'rank', 'phone', 'mobile', 'salary', 'password').\n"
            "2. 'banned_intents': List single keywords and phrases that should trigger immediate query refusal (e.g., 'cgpa', 'gpa', 'marks', 'grade', 'salary', 'phone', 'bypass_attendance', 'cheat_exam').\n"
            "3. 'row_level_security': {'enabled': true, 'user_isolated': true} if users should not see other users' data.\n"
            "4. 'refusal_instructions': Specific system instructions for the LLM.\n"
            "5. 'refusal_message': A polite refusal message.\n\n"
            "Respond ONLY with valid JSON conforming to this schema:\n"
            "{\n"
            '  "banned_intents": ["keyword_or_topic_phrase", ...],\n'
            '  "restricted_columns": ["column_name_to_hide", ...],\n'
            '  "row_level_security": {"enabled": true, "user_isolated": true},\n'
            '  "refusal_instructions": ["directive_for_system_prompt", ...],\n'
            '  "refusal_message": "This information is confidential and protected by privacy policies."\n'
            "}"
        )

        user_prompt = (
            f"Business Restriction Guidelines:\n\"{clean_guidelines}\"\n"
            f"{context_hint}\n\n"
            "Extract the exact banned topics, sensitive database columns, RLS requirements, and refusal instructions."
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = await LLMGateway.complete(
                messages=messages,
                model="qwen/qwen3.8-27b",
                temperature=0.0,
                max_tokens=350
            )

            # Clean json fences if present
            raw = response.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            parsed = json.loads(raw)
            banned = [str(x).lower().strip() for x in parsed.get("banned_intents", []) if str(x).strip()]
            restricted = [str(x).lower().strip() for x in parsed.get("restricted_columns", []) if str(x).strip()]

            # Guarantee core field coverage if guidelines mention them
            low_guide = clean_guidelines.lower()
            if any(k in low_guide for k in ["gpa", "cgpa", "marks", "grade", "score", "ranking", "disciplinary"]):
                restricted.extend(["cgpa", "gpa", "sgpa", "marks", "grade", "score", "rank", "ranking", "percentage"])
                banned.extend(["cgpa", "gpa", "marks", "grade", "student_marks", "another_student"])
            if any(k in low_guide for k in ["phone", "mobile", "contact", "salary", "compensation"]):
                restricted.extend(["phone", "phone_number", "mobile", "salary", "compensation"])
                banned.extend(["phone", "salary"])

            return {
                "banned_intents": list(set(banned)),
                "restricted_columns": list(set(restricted)),
                "row_level_security": parsed.get("row_level_security", {"enabled": True, "user_isolated": True}),
                "refusal_instructions": [str(x).strip() for x in parsed.get("refusal_instructions", []) if str(x).strip()],
                "refusal_message": parsed.get("refusal_message") or cls.DEFAULT_FALLBACK_REFUSAL,
                "raw_guidelines": clean_guidelines
            }
        except Exception as e:
            logger.warning(f"LLM guardrail compile failed: {e}. Using deterministic heuristic compiler.")
            return cls._heuristic_compile(clean_guidelines)

    @classmethod
    def _heuristic_compile(cls, text: str) -> Dict[str, Any]:
        """
        Deterministic rule-based compiler fallback if LLM is unavailable.
        """
        low = text.lower()
        banned = []
        restricted_cols = []
        instructions = []

        # Attendance / Bypass patterns
        if any(w in low for w in ["attendance", "bypass", "cheat", "fake", "loophole", "exam", "pass", "skip"]):
            banned.extend(["bypass_attendance", "fake_medical", "fake_certificate", "exam_cheat", "attendance_loophole", "bypass_rules", "bypass", "cheat"])
            instructions.append("Never provide instructions on how to bypass, cheat, or manipulate attendance, exams, or institutional policies.")

        # Privacy / Personal info patterns
        if any(w in low for w in ["phone", "mobile", "contact", "email", "address", "number"]):
            restricted_cols.extend(["phone", "phone_number", "mobile", "contact_no", "contact_number", "address", "email"])
            banned.extend(["student_phone", "personal_contact", "staff_phone", "phone"])
            instructions.append("Never disclose personal phone numbers, emails, or contact information.")

        # Financial / Salary patterns
        if any(w in low for w in ["salary", "fee", "bank", "payment", "cost", "wage", "compensation"]):
            restricted_cols.extend(["salary", "bank_account", "password", "password_hash", "token", "ssn", "compensation"])
            banned.extend(["salary", "compensation"])
            instructions.append("Never disclose internal salaries, banking details, or security credentials.")

        # Grade / Mark / CGPA privacy
        if any(w in low for w in ["marks", "grades", "score", "student", "another", "gpa", "cgpa", "ranking", "grade"]):
            restricted_cols.extend(["cgpa", "gpa", "sgpa", "marks", "grade", "score", "rank", "ranking", "percentage", "grades"])
            banned.extend(["cgpa", "gpa", "student_marks", "student_grades", "student_cgpa", "view_marks", "another_student"])
            instructions.append("Do not allow users to view other students' private grades, marks, CGPA, GPA, or rankings.")

        if not instructions:
            instructions.append("Follow strict data privacy and do not assist with bypassing regulations.")

        return {
            "banned_intents": list(set(banned)),
            "restricted_columns": list(set(restricted_cols)),
            "row_level_security": {
                "enabled": True,
                "user_isolated": True
            },
            "refusal_instructions": instructions,
            "refusal_message": cls.DEFAULT_FALLBACK_REFUSAL,
            "raw_guidelines": text
        }

    @classmethod
    def _default_guardrail_config(cls) -> Dict[str, Any]:
        return {
            "banned_intents": [],
            "restricted_columns": ["password", "password_hash", "secret", "token"],
            "row_level_security": {"enabled": False, "user_isolated": False},
            "refusal_instructions": [],
            "refusal_message": cls.DEFAULT_FALLBACK_REFUSAL,
            "raw_guidelines": ""
        }

    @classmethod
    def evaluate_query(
        cls,
        query: str,
        guardrail_config: Optional[Dict[str, Any]],
        user_role: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Gate 1: Ultra-fast sub-1ms check before invoking LLM or SQL execution.
        Supports both universal banned intents and role-scoped banned intents.
        Returns: (is_blocked: bool, refusal_message: Optional[str])
        """
        if not query or not guardrail_config:
            return False, None

        q_low = query.lower().strip()
        banned_intents = list(guardrail_config.get("banned_intents", []))
        restricted_cols = [str(c).lower().strip() for c in guardrail_config.get("restricted_columns", [])]
        refusal_msg = guardrail_config.get("refusal_message") or cls.DEFAULT_FALLBACK_REFUSAL

        # 0. Role-scoped banned intent inclusion
        if user_role and isinstance(guardrail_config, dict):
            role_scoped = guardrail_config.get("role_scoped_bans", {})
            if isinstance(role_scoped, dict):
                role_bans = role_scoped.get(user_role.lower()) or role_scoped.get(user_role) or []
                if isinstance(role_bans, list):
                    banned_intents.extend(role_bans)

        # Universal bypass & jailbreak indicators
        universal_bypass_triggers = [
            "bypass", "cheat", "fake medical", "fake certificate", "fake attendance",
            "hack exam", "hack attendance", "loophole to avoid", "how to skip attendance",
            "tricks to bypass", "trick to bypass", "ignore previous instructions", "jailbreak"
        ]

        # 1. Universal trigger check
        for trig in universal_bypass_triggers:
            if trig in q_low:
                return True, refusal_msg

        # Check if role is elevated management / staff (e.g. TPO, Admin, Faculty)
        ELEVATED_ROLES = {"admin", "tpo", "placement_officer", "faculty", "staff", "management", "manager", "superadmin", "recruiter", "director", "dean"}
        role_is_elevated = bool(user_role and user_role.lower() in ELEVATED_ROLES)

        # Check if the query is a self-inquiry for personal metrics
        is_self_query = bool(re.search(r"\b(my|mine|me|myself|i am|for me)\b", q_low))

        # Academic & departmental operational metrics permissible for self-service or elevated roles
        ACADEMIC_METRIC_FIELDS = {"cgpa", "gpa", "sgpa", "marks", "attendance", "grade", "grades", "score", "scores", "rank", "percentage"}

        # 2. Direct Restricted Column & PII extraction check
        for col in restricted_cols:
            if not col or len(col) < 3:
                continue
            col_lower = col.lower().strip()
            # Allow academic/performance metrics for elevated roles (TPO/faculty) or self-queries
            if col_lower in ACADEMIC_METRIC_FIELDS and (role_is_elevated or is_self_query):
                continue
            # Regex word boundary check to avoid false positives on substrings
            if re.search(rf"\b{re.escape(col)}\b", q_low):
                return True, refusal_msg
            if "_" in col:
                col_spaced = col.replace("_", " ")
                if re.search(rf"\b{re.escape(col_spaced)}\b", q_low):
                    return True, refusal_msg

        # 3. Configured banned intent check (Universal + Role-scoped)
        for intent in banned_intents:
            intent_clean = intent.replace("_", " ").lower().strip()
            if not intent_clean:
                continue
            
            # Allow academic/performance metrics for elevated roles or self-queries
            if intent_clean in ACADEMIC_METRIC_FIELDS and (role_is_elevated or is_self_query):
                continue

            # Single word intent check (e.g. 'salary', 'secret')
            if " " not in intent_clean and len(intent_clean) >= 3:
                if re.search(rf"\b{re.escape(intent_clean)}\b", q_low):
                    return True, refusal_msg
            else:
                # Multi-word intent check
                tokens = [t for t in intent_clean.split() if len(t) > 3]
                if tokens and all(tok in q_low for tok in tokens):
                    return True, refusal_msg

        return False, None
