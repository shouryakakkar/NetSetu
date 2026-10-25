"""
NLP Classifier using HuggingFace zero-shot classification.

Model: facebook/bart-large-mnli (local, CPU, no API key required).
The model is lazy-loaded on first request and cached in memory.

Purpose: given an unrecognized CLI syntax line, suggest the closest
         SecurityBaselineModel field name with a confidence score.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Mapping of clean baseline parameter -> natural language security description for BART
LABEL_DESCRIPTIONS: dict[str, str] = {
    "ssh_version": "SSH protocol version and secure shell remote access configuration",
    "ssh_enabled": "enabling SSH secure shell server service",
    "telnet_enabled": "insecure Telnet plaintext remote access service",
    "vty_acl_applied": "access control list or filter applied to terminal VTY lines",
    "vty_transport_input_ssh_only": "restricting terminal transport input to SSH only",
    "console_timeout": "console line inactivity session timeout",
    "vty_timeout": "VTY virtual terminal session inactivity timeout",
    "snmp_version": "SNMP network management protocol version and security level",
    "snmp_community_public": "SNMP default community string like public or private",
    "ntp_configured": "NTP network time protocol synchronization server",
    "ntp_authentication_enabled": "NTP authentication cryptographic key validation",
    "aaa_enabled": "AAA authentication authorization and accounting framework",
    "aaa_new_model": "Cisco AAA new-model authentication system",
    "password_encryption_service": "reversibly encrypting plaintext passwords in configuration",
    "enable_secret_set": "privileged enable secret password hash",
    "http_server_enabled": "unencrypted HTTP web management server",
    "https_server_enabled": "secure HTTPS TLS web management server",
    "banner_motd_set": "security warning banner or message of the day login disclaimer",
    "banner_login_set": "login banner legal disclaimer",
    "logging_enabled": "system audit event logging and syslog recording",
    "logging_remote_host": "remote syslog logging collector server host",
    "bgp_md5_auth": "BGP routing peer MD5 authentication password",
    "cdp_enabled": "Cisco Discovery Protocol neighbor discovery",
    "lldp_enabled": "Link Layer Discovery Protocol neighbor discovery",
    "spanning_tree_bpduguard": "Spanning Tree BPDU Guard edge port protection",
    "port_security_enabled": "switchport port security and MAC address limiting",
    "dhcp_snooping": "DHCP snooping security trust inspection",
    "dynamic_arp_inspection": "Dynamic ARP Inspection DAI protection",
}

CANDIDATE_PHRASES: list[str] = list(LABEL_DESCRIPTIONS.values())
PHRASE_TO_LABEL: dict[str, str] = {v: k for k, v in LABEL_DESCRIPTIONS.items()}


@dataclass
class SuggestionResult:
    label: str
    score: float
    raw_line: str


@lru_cache(maxsize=1)
def _load_pipeline() -> Any:
    """Lazy-load the zero-shot classification pipeline (singleton)."""
    try:
        from transformers import pipeline  # type: ignore
        logger.info("Loading HuggingFace zero-shot model: %s", settings.hf_model_name)
        clf = pipeline(
            "zero-shot-classification",
            model=settings.hf_model_name,
            device=-1,  # CPU
            cache_dir=settings.model_cache_dir,
        )
        logger.info("Model loaded successfully.")
        return clf
    except Exception as exc:
        logger.error("Failed to load HuggingFace model: %s", exc)
        return None


def classify_syntax(raw_line: str, top_k: int = 3) -> list[SuggestionResult]:
    """
    Classify a raw unrecognized CLI line against all candidate security
    parameter labels using natural language descriptions and NLI hypothesis templates.
    """
    if not raw_line or len(raw_line.strip()) < 4:
        return []

    clf = _load_pipeline()
    if clf is None:
        return []

    try:
        # Evaluate with natural language hypothesis template
        result = clf(
            raw_line.strip(),
            candidate_labels=CANDIDATE_PHRASES,
            hypothesis_template="This network command configures {}.",
            multi_label=False,
        )
        suggestions = []
        for phrase, score in zip(result["labels"], result["scores"]):
            canonical_label = PHRASE_TO_LABEL.get(phrase, phrase)
            suggestions.append(
                SuggestionResult(label=canonical_label, score=round(score, 4), raw_line=raw_line)
            )

        # Deduplicate and sort
        seen = set()
        deduped = []
        for s in sorted(suggestions, key=lambda x: x.score, reverse=True):
            if s.label not in seen:
                seen.add(s.label)
                deduped.append(s)

        return deduped[:top_k]
    except Exception as exc:
        logger.error("Classification error: %s", exc)
        return []
