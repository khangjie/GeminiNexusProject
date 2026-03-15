"""
Receipt Processing Pipeline — ADK multi-agent implementation.

Auto-Approval Flow (matches ProjectStructure.litcoffee):

  User Upload Receipt
          │
          ▼
  SequentialAgent: extraction_pipeline
          ├── receipt_parser_agent        (refines OCR text → structured JSON)
          └── receipt_type_classifier     (proposal | paid_expense)
          │
          ▼
  ParallelAgent: validation_pipeline
          ├── rule_checker_agent          (evaluates owner-defined rules)
          ├── pre_approved_detector       (checks pre-approved item list)
          └── duplicate_detector          (compares to recent receipts)
          │
          ▼
  decision_agent                          (combines signals → status)
          │
          ▼
  categorization_agent                    (assigns expense category per item)

Public API:
    run_receipt_approval_pipeline(receipt, db) -> dict
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agents._runner import (
    ADK_AVAILABLE,
    Agent,
    FunctionTool,
    ParallelAgent,
    SequentialAgent,
    _get_gemini_model,
    _safe_json,
    run_adk_pipeline,
)
from agents.tools import (
    approval_rules_tool,
    pre_approved_items_tool,
    recent_receipts_tool,
    set_pipeline_context,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MODEL = settings.GEMINI_MODEL  # e.g. "gemini-1.5-flash"

# ── Individual Agent Definitions ──────────────────────────────────────────────

def _build_agents():
    """Build and return all receipt pipeline agents.  Called lazily so imports
    don't fail when ADK is unavailable."""
    if not ADK_AVAILABLE:
        return None

    # 1. Receipt Parser Agent — converts raw OCR text to structured JSON
    receipt_parser = Agent(
        name="receipt_parser_agent",
        model=MODEL,
        instruction="""You are the Receipt Parser Agent in an expense management system.

Your task is to take raw OCR-extracted text from a receipt and output a clean,
structured JSON object with the following fields:
  - vendor: string (store/company name)
  - total_amount: number (final amount paid)
  - receipt_date: string (ISO date YYYY-MM-DD, or null)
  - receipt_type_hint: "proposal" | "paid_expense" | "unknown"
  - items: array of { name: string, price: number | null }

Rules:
- Extract ALL line items you can identify.
- If a field is uncertain, make your best guess rather than null.
- Output ONLY the JSON object, no additional text.
""",
        output_key="parsed_receipt",
    )

    # 2. Receipt Type Classifier — proposal vs paid_expense
    type_classifier = Agent(
        name="receipt_type_classifier",
        model=MODEL,
        instruction="""You are the Receipt Type Classifier Agent.

Based on the parsed receipt data from the previous agent, determine whether this
receipt is a:
  - "proposal"     : Payment has NOT yet been made (quotation, purchase order, etc.)
  - "paid_expense" : Payment has ALREADY been made (invoice, receipt, reimbursement)

Respond with a JSON object:
{
  "receipt_type": "proposal" | "paid_expense",
  "confidence": "high" | "medium" | "low",
  "reasoning": "brief explanation"
}

Output ONLY the JSON object.
""",
        output_key="receipt_type_result",
    )

    # 3. Rule Checker Agent — evaluates owner-defined approval rules
    rule_checker = Agent(
        name="rule_checker_agent",
        model=MODEL,
        instruction="""You are the Rule Checking Agent in an expense management system.

Use the `fetch_approval_rules` tool to retrieve the company's active approval rules,
then evaluate each rule against the receipt data provided in the conversation.

For each rule, determine if it PASSES or FAILS based on the receipt content.
Each rule may include `applies_to_preapproved`.
Copy that boolean into your output for each rule.

Respond with a JSON object:
{
  "rule_checks": [
    {
      "rule_name": "name of the rule",
      "rule_text": "the rule prompt text",
      "applies_to_preapproved": true | false,
      "passed": true | false,
      "explanation": "why it passed or failed"
    }
  ],
  "overall_rules_passed": true | false
}

Output ONLY the JSON object.
""",
        tools=[approval_rules_tool],
        output_key="rule_check_result",
    )

    # 4. Pre-Approved Item Detector
    pre_approved_detector = Agent(
        name="pre_approved_detector",
        model=MODEL,
        instruction="""You are the Pre-Approved Item Detection Agent.

Use the `fetch_pre_approved_items` tool to retrieve the company's pre-approved
item configurations, then check if any items in the current receipt match them.

Matching criteria:
- Item name similarity (fuzzy match is fine)
- Amount within the configured limit (if specified)

Respond with a JSON object:
{
  "has_pre_approved_match": true | false,
  "matched_items": [
    {
      "receipt_item": "item name from receipt",
      "pre_approved_config": "config name that matched",
      "within_limit": true | false
    }
  ],
  "note": "brief explanation"
}

Output ONLY the JSON object.
""",
        tools=[pre_approved_items_tool],
        output_key="pre_approved_result",
    )

    # 5. Duplicate Detector Agent
    duplicate_detector = Agent(
        name="duplicate_detector",
        model=MODEL,
        instruction="""You are the Duplicate Detection Agent.

Use the `fetch_recent_receipts` tool to retrieve recent company receipts,
then compare them to the current receipt.

Duplicate criteria (any combination):
- Same or very similar vendor name
- Same or very similar total amount
- Same or very close date

Respond with a JSON object:
{
  "is_duplicate": true | false,
  "duplicate_receipt_id": "id of the suspected duplicate" | null,
  "duplicate_vendor": "vendor name" | null,
  "similarity_score": 0.0-1.0,
  "reasoning": "brief explanation"
}

Output ONLY the JSON object.
""",
        tools=[recent_receipts_tool],
        output_key="duplicate_result",
    )

    # 6. Decision Agent — combines all validation signals
    decision_agent = Agent(
        name="decision_agent",
        model=MODEL,
        instruction="""You are the Decision Agent — the final authority in the receipt
approval pipeline.

You have access to the results from:
  - receipt_parser_agent      → parsed receipt structure
  - receipt_type_classifier   → receipt type (proposal | paid_expense)
  - rule_checker_agent        → rule check results (passed/failed)
  - pre_approved_detector     → pre-approved item matches
  - duplicate_detector        → duplicate detection results

Based on ALL of these signals, make a final decision:
  - "ai_approved"  : All rules pass, no critical issues
  - "ai_rejected"  : One or more rules explicitly fail
  - "awaiting"     : Ambiguous, needs human review

Important rule for pre-approved items:
- If `pre_approved_detector.has_pre_approved_match` is true, then any failed rule
  where `applies_to_preapproved` is false should NOT count as a rejection.
- Those rules can still be included in the explanation, but they must be treated as
  informational / skipped for decisioning on pre-approved matches.

Respond with a JSON object:
{
  "status": "ai_approved" | "ai_rejected" | "awaiting",
  "verdict": "short label (e.g. Approved, Rejected: Missing Signature)",
  "reason": "detailed explanation for the human reviewer",
  "is_duplicate": true | false,
  "rule_checks": [
    {
      "rule_text": "...",
      "passed": true | false,
      "explanation": "..."
    }
  ]
}

Output ONLY the JSON object.
""",
        output_key="decision_result",
    )

    # 7. Categorization Agent — assigns expense categories
    categorization_agent = Agent(
        name="categorization_agent",
        model=MODEL,
        instruction="""You are the Expense Categorization Agent.

Based on the receipt items extracted earlier in this conversation, assign an
appropriate expense category to each item.

Common categories: Meals, Travel, Software, Hardware, Office Supplies,
Utilities, Marketing, Professional Services, Other.

Respond with a JSON object:
{
  "categories": [
    { "item_name": "...", "category": "..." }
  ],
  "primary_category": "the dominant category for the whole receipt"
}

Output ONLY the JSON object.
""",
        output_key="categorization_result",
    )

    return {
        "receipt_parser": receipt_parser,
        "type_classifier": type_classifier,
        "rule_checker": rule_checker,
        "pre_approved_detector": pre_approved_detector,
        "duplicate_detector": duplicate_detector,
        "decision_agent": decision_agent,
        "categorization_agent": categorization_agent,
    }


def _build_pipeline(agents: dict):
    """Compose agents into the full receipt processing pipeline."""
    extraction_pipeline = SequentialAgent(
        name="extraction_pipeline",
        description="Parses OCR text and classifies receipt type.",
        sub_agents=[
            agents["receipt_parser"],
            agents["type_classifier"],
        ],
    )

    validation_pipeline = ParallelAgent(
        name="validation_pipeline",
        description="Runs rule checking, pre-approval detection, and duplicate detection in parallel.",
        sub_agents=[
            agents["rule_checker"],
            agents["pre_approved_detector"],
            agents["duplicate_detector"],
        ],
    )

    return SequentialAgent(
        name="receipt_processing_pipeline",
        description="Full receipt processing pipeline: OCR → classify → validate → decide → categorize.",
        sub_agents=[
            extraction_pipeline,
            validation_pipeline,
            agents["decision_agent"],
            agents["categorization_agent"],
        ],
    )


# ── Public pipeline runner ────────────────────────────────────────────────────

async def run_receipt_approval_pipeline(receipt: Any, db: Any) -> dict:
    """
    Run the full ADK receipt processing pipeline.

    Falls back to direct Gemini prompts if ADK is unavailable.

    Returns dict with keys:
      status, verdict, reason, is_duplicate, duplicate_of_id, rule_checks
    """
    logger.info(
        "Receipt agent pipeline started for receipt_id=%s company_id=%s",
        getattr(receipt, "id", "unknown"),
        getattr(receipt, "company_id", "unknown"),
    )

    # Inject DB + company context for tool functions
    set_pipeline_context(db=db, company_id=receipt.company_id)

    items_text = "\n".join(
      f"  - {item.name} (qty: {getattr(item, 'quantity', 1) or 1}): {item.price}" for item in receipt.items
    ) or "  (no items extracted)"

    initial_prompt = f"""Receipt submitted for processing:

Vendor: {receipt.vendor or 'Unknown'}
Total Amount: {receipt.total_amount}
Receipt Date: {receipt.receipt_date}
Receipt Type (user-selected): {receipt.receipt_type}
Raw OCR Text:
{receipt.ocr_raw_text or '(not available)'}

Extracted Items:
{items_text}

Please process this receipt through the full pipeline."""

    # ── Try ADK pipeline ──────────────────────────────────────────────────────
    if ADK_AVAILABLE:
        try:
            logger.info("Running receipt approval pipeline via ADK")
            agents = _build_agents()
            pipeline = _build_pipeline(agents)
            final_text = await run_adk_pipeline(pipeline, initial_prompt)
            result = _safe_json(final_text)
            if result.get("status"):
                logger.info(
                    "Receipt agent pipeline completed via ADK with status=%s verdict=%s",
                    result.get("status"),
                    result.get("verdict"),
                )
                return _format_decision_result(result, db)
        except Exception as exc:
            logger.warning("ADK receipt pipeline failed (%s), using Gemini fallback.", exc)

    # ── Gemini direct fallback ────────────────────────────────────────────────
    logger.info("Running receipt approval pipeline via Gemini fallback")
    return await _gemini_fallback_approval(receipt, db, initial_prompt)


def _format_decision_result(result: dict, db: Any) -> dict:
    """Normalize ADK pipeline JSON output to the expected return schema."""
    from app.models.approval_rule import ApprovalRule
    company_id = _company_id_ctx_val()

    rule_checks = []
    rules = []
    if db and company_id:
        rules = db.query(ApprovalRule).filter(
            ApprovalRule.company_id == company_id,
            ApprovalRule.is_active == True,
        ).all()

    for i, check in enumerate(result.get("rule_checks", [])):
        rule_id = rules[i].id if i < len(rules) else None
        rule_checks.append({
            "rule_id": rule_id,
            "rule_text": check.get("rule_text", ""),
            "passed": check.get("passed", True),
            "explanation": check.get("explanation"),
        })

    return {
        "status": result.get("status", "awaiting"),
        "verdict": result.get("verdict", "Pending Review"),
        "reason": result.get("reason", ""),
        "is_duplicate": result.get("is_duplicate", False),
        "duplicate_of_id": result.get("duplicate_receipt_id"),
        "rule_checks": rule_checks,
    }


def _company_id_ctx_val() -> str:
    from agents.tools import _company_id_ctx
    return _company_id_ctx.get("")


# ── Gemini direct fallback (mirrors old gemini_service logic) ─────────────────

async def _gemini_fallback_approval(receipt: Any, db: Any, _prompt: str) -> dict:
    """Direct Gemini API fallback — used when ADK is unavailable or errors."""
    model = _get_gemini_model(settings.GEMINI_MODEL)
    if not model:
        return {
            "status": "awaiting",
            "verdict": "Pending Review",
            "reason": "AI service unavailable. Manual review required.",
            "is_duplicate": False,
            "duplicate_of_id": None,
            "rule_checks": [],
        }

    from app.models.approval_rule import ApprovalRule
    from app.core.pre_approved_meta import decode_pre_approved_meta
    from app.models.pre_approved_item import PreApprovedItem
    from app.models.receipt import Receipt as ReceiptModel

    rules = db.query(ApprovalRule).filter(
        ApprovalRule.company_id == receipt.company_id,
        ApprovalRule.is_active == True,
    ).all()

    pre_approved = db.query(PreApprovedItem).filter(
        PreApprovedItem.company_id == receipt.company_id,
        PreApprovedItem.is_active == True,
    ).all()

    recent = db.query(ReceiptModel).filter(
        ReceiptModel.company_id == receipt.company_id,
        ReceiptModel.id != receipt.id,
    ).order_by(ReceiptModel.created_at.desc()).limit(20).all()

    items_text = "\n".join(
      f"- {i.name} (qty: {getattr(i, 'quantity', 1) or 1}): {i.price}" for i in receipt.items
    ) or "None"
    rules_text = "\n".join(f"{n+1}. {r.name}: {r.prompt}" for n, r in enumerate(rules)) or "No rules defined"
    pre_lines: list[str] = []
    for p in pre_approved:
      note, custom_variables = decode_pre_approved_meta(p.note)
      vars_text = ", ".join(f"{k}={v}" for k, v in custom_variables.items()) if custom_variables else ""
      suffix_parts = [f"limit: {p.amount_limit}"]
      if note:
        suffix_parts.append(f"note: {note}")
      if vars_text:
        suffix_parts.append(f"vars: {vars_text}")
      pre_lines.append(f"- {p.item_name} ({'; '.join(suffix_parts)})")
    pre_text = "\n".join(pre_lines) or "None"
    recent_text = "\n".join(f"- {r.vendor} | {r.total_amount} | {r.receipt_date}" for r in recent[:10])

    prompt = f"""You are the AI Decision Agent for an expense management system.

Receipt Details:
  Vendor: {receipt.vendor}
  Total:  {receipt.total_amount}
  Type:   {receipt.receipt_type}
  Date:   {receipt.receipt_date}
  Items:
{items_text}

Owner Approval Rules:
{rules_text}

Pre-Approved Items:
{pre_text}

Recent Receipts (for duplicate detection):
{recent_text}

Evaluate and respond with ONLY a JSON object:
{{
  "status": "ai_approved" | "ai_rejected" | "awaiting",
  "verdict": "short label",
  "reason": "detailed explanation",
  "is_duplicate": true | false,
  "duplicate_vendor": "vendor name if duplicate" | null,
  "rule_checks": [
    {{"rule_text": "...", "passed": true | false, "explanation": "..."}}
  ]
}}"""

    try:
        response = model.generate_content(prompt)
        result = _safe_json(response.text)
    except Exception as exc:
        logger.error("Gemini fallback error: %s", exc)
        result = {}

    rule_checks = []
    for i, check in enumerate(result.get("rule_checks", [])):
        rule_checks.append({
            "rule_id": rules[i].id if i < len(rules) else None,
            "rule_text": check.get("rule_text", ""),
            "passed": check.get("passed", True),
            "explanation": check.get("explanation"),
        })

    return {
        "status": result.get("status", "awaiting"),
        "verdict": result.get("verdict", "Pending Review"),
        "reason": result.get("reason", ""),
        "is_duplicate": result.get("is_duplicate", False),
        "duplicate_of_id": None,
        "rule_checks": rule_checks,
    }
