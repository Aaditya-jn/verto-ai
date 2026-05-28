# handlers/sandbox_handler.py

ACTIVATION_KEYWORDS = ["join", "hello", "hi", "start", "hey", "helo", "नमस्ते", "namaste"]

ACTIVATION_REPLY = """Verto AI Sandbox: ✅ You are all set! The sandbox can now send/receive messages from whatsapp:+14155238886. Reply stop to leave the sandbox any time.

Additionally the default language for conversation is English 
Here are the currently supported languages you can choose from these:

1. Hindi
2. Marathi
3. Gujarati

Reply with 1, 2, or 3 to switch your language. Otherwise, just send any news to fact-check! 🔍"""

LANGUAGE_MAP = {
    "1": "Hindi",
    "2": "Marathi",
    "3": "Gujarati",
    "hindi": "Hindi",
    "marathi": "Marathi",
    "gujarati": "Gujarati"
}

LANGUAGE_CONFIRMED = {
    "Hindi": "✅ भाषा हिंदी में सेट की गई। अब कोई भी खबर भेजें, हम जाँच करेंगे! 🔍",
    "Marathi": "✅ भाषा मराठीमध्ये सेट केली. आता कोणतीही बातमी पाठवा, आम्ही तपासू! 🔍",
    "Gujarati": "✅ ભાષા ગુજરાતીમાં સેટ કરી. હવે કોઈ પણ સમાચાર મોકલો, અમે તપાસ કરીશું! 🔍"
}


def is_activation_message(text: str) -> bool:
    text_lower = text.lower().strip()
    if len(text.strip()) > 40:
        return False
    return any(kw in text_lower for kw in ACTIVATION_KEYWORDS)


def is_language_selection(text: str) -> str | None:
    return LANGUAGE_MAP.get(text.strip().lower())
