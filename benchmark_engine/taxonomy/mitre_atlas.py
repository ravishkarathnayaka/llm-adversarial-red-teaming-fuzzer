"""MITRE ATLAS and NIST AI RMF taxonomy mapping for AI Safety & Robustness evaluation."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AtlasTactic(str, Enum):
    INITIAL_ACCESS = "AML.TA0001"
    ML_ATTACK_STAGING = "AML.TA0002"
    DISCOVERY = "AML.TA0003"
    EXFILTRATION = "AML.TA0004"
    EVASION = "AML.TA0005"
    IMPACT = "AML.TA0006"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AtlasTechnique(BaseModel):
    id: str = Field(..., description="MITRE ATLAS Technique ID (e.g. AML.T0051)")
    name: str = Field(..., description="Descriptive name of the technique")
    tactic: AtlasTactic = Field(..., description="Parent tactic category")
    description: str = Field(..., description="Detailed description of the threat vector")
    risk_level: RiskLevel = Field(..., description="Inherent severity rating")
    nist_category: str = Field(..., description="Mapped NIST AI RMF category (e.g. MEASURE 2.5)")
    owasp_llm_id: str = Field(..., description="Mapped OWASP Top 10 for LLM Applications")
    recommended_mitigation: str = Field(..., description="Mitigation strategy for target model")


# Complete MITRE ATLAS Matrix for LLM Robustness & Safety Evaluation
ATLAS_TECHNIQUES: Dict[str, AtlasTechnique] = {
    "AML.T0051": AtlasTechnique(
        id="AML.T0051",
        name="LLM Prompt Injection",
        tactic=AtlasTactic.INITIAL_ACCESS,
        description="Adversary crafts inputs designed to override original instructions, guardrails, or system parameters.",
        risk_level=RiskLevel.CRITICAL,
        nist_category="MEASURE 2.5 (Adversarial Robustness)",
        owasp_llm_id="LLM01: Prompt Injection",
        recommended_mitigation="Enforce strict delimiter separation, dual-LLM instruction gating, and input sanitization.",
    ),
    "AML.T0054": AtlasTechnique(
        id="AML.T0054",
        name="LLM Jailbreak",
        tactic=AtlasTactic.EVASION,
        description="Adversary bypasses safety filters via persona framing, hypothetical scenarios, or multi-turn conversational traps.",
        risk_level=RiskLevel.CRITICAL,
        nist_category="MANAGE 2.3 (Policy Adherence)",
        owasp_llm_id="LLM01: Prompt Injection / Safety Bypass",
        recommended_mitigation="Employ multi-turn conversational alignment checks, RLHF guardrail tuning, and semantic policy judges.",
    ),
    "AML.T0056": AtlasTechnique(
        id="AML.T0056",
        name="Extract Model Artifacts (System Prompt Leakage)",
        tactic=AtlasTactic.EXFILTRATION,
        description="Adversary probes the model to disclose confidential system instructions, internal schemas, or embedded canary tokens.",
        risk_level=RiskLevel.HIGH,
        nist_category="GOVERN 1.2 (Confidentiality & Integrity)",
        owasp_llm_id="LLM06: Sensitive Information Disclosure",
        recommended_mitigation="Implement post-generation canary token filtering and strict confidentiality prompts.",
    ),
    "AML.T0048": AtlasTechnique(
        id="AML.T0048",
        name="Model Evasion via Obfuscation",
        tactic=AtlasTactic.EVASION,
        description="Adversary encodes payloads (Base64, ROT13, Leetspeak, multi-language) to bypass lexical safety classifiers.",
        risk_level=RiskLevel.HIGH,
        nist_category="MEASURE 2.6 (Input Transformation Resilience)",
        owasp_llm_id="LLM01: Obfuscated Prompt Injection",
        recommended_mitigation="Decode and normalize encoded inputs prior to safety evaluation and safety filter layers.",
    ),
    "AML.T0055": AtlasTechnique(
        id="AML.T0055",
        name="Insecure Output Handling / Evasion",
        tactic=AtlasTactic.IMPACT,
        description="Target model produces unescaped markdown, scripts, or formatted payloads that induce downstream execution risk.",
        risk_level=RiskLevel.MEDIUM,
        nist_category="MANAGE 2.4 (Output Integrity)",
        owasp_llm_id="LLM02: Insecure Output Handling",
        recommended_mitigation="Context-aware output encoding, strict content sandboxing, and output sanitization.",
    ),
    "AML.T0043": AtlasTechnique(
        id="AML.T0043",
        name="Craft Adversarial Edge Cases",
        tactic=AtlasTactic.ML_ATTACK_STAGING,
        description="Systematically mutates benign queries into ambiguous or edge-case boundary scenarios.",
        risk_level=RiskLevel.MEDIUM,
        nist_category="MAP 1.5 (Threat Modeling)",
        owasp_llm_id="LLM01: Adversarial Perturbations",
        recommended_mitigation="Automated continuous multi-turn adversarial stress testing and reinforcement learning alignment.",
    ),
}


def get_technique(technique_id: str) -> Optional[AtlasTechnique]:
    """Retrieve MITRE ATLAS technique definition by ID."""
    return ATLAS_TECHNIQUES.get(technique_id)


def list_techniques() -> List[AtlasTechnique]:
    """Return all supported ATLAS techniques."""
    return list(ATLAS_TECHNIQUES.values())


def get_techniques_by_tactic(tactic: AtlasTactic) -> List[AtlasTechnique]:
    """Filter techniques by tactic category."""
    return [tech for tech in ATLAS_TECHNIQUES.values() if tech.tactic == tactic]
