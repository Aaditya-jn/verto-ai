# handlers/reply_formatter.py

VERDICT_EMOJI = {
    "REAL": "✅",
    "FAKE": "❌",
    "MISLEADING": "⚠️",
    "UNVERIFIED": "❓"
}

VERDICT_LABEL = {
    "REAL": "Verified Real News",
    "FAKE": "Fake News Detected",
    "MISLEADING": "Possibly Misleading News",
    "UNVERIFIED": "Could Not Verify"
}


def format_english_verdict(verdict: str, explanation: str, evidence: str,
                            sources: list, confidence: str, hashtags: str) -> str:
    emoji = VERDICT_EMOJI.get(verdict.upper(), "❓")
    label = VERDICT_LABEL.get(verdict.upper(), verdict)
    sources_text = "\n".join([f"• {s}" for s in sources]) if sources else "• No verified source found."

    return f"""{emoji} {label}

{explanation}

🔍 Supportive Evidence (Based on Available Reports):
{evidence}

📚 Sources:
{sources_text}

⚠️ Note: This content is shared only for analysis. Spreading unverified claims can contribute to misinformation.

{hashtags}"""
