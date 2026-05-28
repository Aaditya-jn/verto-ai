# agent/deep_agent.py
import os
import json
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
from langchain_deepagent import DeepAgent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# Global state for persistent sessions
global_mcp_client = None
global_verto_session_ctx = None
global_verto_session = None
global_tavily_session_ctx = None
global_tavily_session = None
global_mcp_tools = None

TAVILY_MCP_URL = "https://mcp.tavily.com/mcp/?tavilyApiKey=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"

SYSTEM_PROMPT = """
You are Verto AI, an expert multilingual fake news detection agent.

TOOLS AVAILABLE (call all that apply before concluding):
- extract_text_from_image: Use when input contains MEDIA_TYPE:image
- extract_text_from_video: Use when input contains MEDIA_TYPE:video
- extract_text_from_document: Use when input contains MEDIA_TYPE:document
- tavily_search: Search the open web for real-time news and facts about a claim
- tavily_research: Perform a deep comprehensive search when tavily_search results are insufficient
- translate_text: Use when input starts with TRANSLATE_ONLY:

WORKFLOW:
1. If input starts with TRANSLATE_ONLY: translate the text after it and return translation only, no JSON.
2. If input contains MEDIA_TYPE: extract the claim using the right extraction tool first.
3. Use tavily_search to find what actually happened around this claim. Include real news site domains in your query.
4. If you need deeper verification, use tavily_research with the claim as the query.
5. Analyze all results carefully:
   - Is the location correct?
   - Are the people mentioned real and correctly identified?
   - Are numbers/statistics accurate?
   - Is context missing or exaggerated?
6. Decide verdict: REAL, FAKE, or MISLEADING
7. Return ONLY a valid JSON object with this exact structure:

{{
  "verdict": "MISLEADING",
  "explanation": "2-3 sentence explanation of what is true, what is wrong, and why it is misleading.",
  "evidence": "1-2 sentences summarizing what the search results actually show.",
  "sources": [
    "https://actual-url-from-search-results.com/article"
  ],
  "confidence": "High / Medium / Low",
  "hashtags": "#Misleading #FactCheck #VerificationNeeded"
}}

CRITICAL RULES FOR SOURCES — MANDATORY:
- After calling tools, scan ALL tool output line by line.
- Every URL that appears in tool output is a real URL — copy the FULL URL verbatim into "sources".
- NEVER paraphrase, shorten, or fabricate URLs. Copy them exactly character-for-character.
- Include ALL URLs you found, not just 1. The more real sources the better.
- Only use ["No verified source found."] if and ONLY IF zero URLs appeared in any tool output.
- VERDICT-SPECIFIC SOURCE SELECTION:
  * If the verdict is FAKE or MISLEADING:
    - The "sources" list MUST contain URLs of fact-check articles or credible reports that debunk the claim or show the actual truth.
    - NEVER link to the fake news site, rumor post, or fabricate a URL to the false claim.
  * If the verdict is REAL:
    - The "sources" list MUST contain the verified direct URLs of the credible news outlets reporting that event.
- Be nuanced. MISLEADING is valid when facts are partially true but location/person/severity is wrong.
- Think step by step. Use at least 2 tools before concluding.
- Return ONLY the JSON. No preamble, no markdown fences.
"""


async def startup_mcp():
    """Initialize persistent MCP client sessions for both verto-mcp and Tavily MCP."""
    global global_mcp_client, global_verto_session_ctx, global_verto_session
    global global_tavily_session_ctx, global_tavily_session, global_mcp_tools

    if global_mcp_client is not None:
        return

    logger = logging.getLogger("__main__")
    logger.info("🔗 [MCP] Initializing persistent MultiServerMCPClient (verto + Tavily)...")

    mcp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_server.py"))
    print(f"🔗 [MCP] Spawning verto MCP server from: {mcp_path}")

    global_mcp_client = MultiServerMCPClient({
        "verto-mcp": {
            "command": "/home/aaditya/Desktop/verto_ai/verto_ai/venv/bin/python",
            "args": ["-u", mcp_path],
            "transport": "stdio",
            "env": {
                "PYTHONDONTWRITEBYTECODE": "1"
            }
        },
        "tavily": {
            "url": TAVILY_MCP_URL,
            "transport": "streamable_http"
        }
    })

    # ── Open verto-mcp session ──────────────────────────────────────────────────
    global_verto_session_ctx = global_mcp_client.session("verto-mcp")
    global_verto_session = await global_verto_session_ctx.__aenter__()
    verto_tools = await load_mcp_tools(global_verto_session)
    logger.info(f"✅ [MCP] verto-mcp started. Loaded {len(verto_tools)} tools.")

    # ── Open Tavily MCP session ─────────────────────────────────────────────────
    try:
        global_tavily_session_ctx = global_mcp_client.session("tavily")
        global_tavily_session = await global_tavily_session_ctx.__aenter__()
        tavily_tools = await load_mcp_tools(global_tavily_session)
        logger.info(f"✅ [MCP] Tavily MCP connected. Loaded {len(tavily_tools)} tools: {[t.name for t in tavily_tools]}")
    except Exception as e:
        logger.error(f"⚠️ [MCP] Tavily MCP connection failed: {e}. Web search may be limited.")
        tavily_tools = []

    # Merge tools from both servers — agent sees all of them
    global_mcp_tools = verto_tools + tavily_tools
    logger.info(f"✅ [MCP] Total tools available to agent: {len(global_mcp_tools)}")


async def shutdown_mcp():
    """Safely shut down both persistent MCP sessions during application teardown."""
    global global_mcp_client, global_verto_session_ctx, global_verto_session
    global global_tavily_session_ctx, global_tavily_session, global_mcp_tools

    logger = logging.getLogger("__main__")
    logger.info("🔌 [MCP] Shutting down persistent MCP sessions...")

    for name, ctx in [("verto-mcp", global_verto_session_ctx), ("tavily", global_tavily_session_ctx)]:
        if ctx is not None:
            try:
                await ctx.__aexit__(None, None, None)
                logger.info(f"✅ [MCP] {name} session closed.")
            except Exception as e:
                logger.error(f"⚠️ [MCP] Error closing {name} session: {e}")

    global_mcp_client = None
    global_verto_session_ctx = None
    global_verto_session = None
    global_tavily_session_ctx = None
    global_tavily_session = None
    global_mcp_tools = None


async def run_detector_agent(user_input: str) -> dict:
    global global_mcp_client, global_verto_session, global_tavily_session, global_mcp_tools
    print(f"🚀 [DEEP_AGENT] Called with input: {user_input[:200]}")
    logger = logging.getLogger("__main__")

    # Reconnect/startup safety check
    if global_mcp_client is None or global_mcp_tools is None:
        logger.warning("⚠️ [AGENT] MCP client not initialized. Reconnecting/starting now...")
        await startup_mcp()

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-lite-latest",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.1,
        max_retries=2,
    )

    agent = DeepAgent(
        llm=llm,
        tools=global_mcp_tools,
        system_prompt=SYSTEM_PROMPT,
        max_iterations=10,
        verbose=True
    )

    # Retry loop with exponential backoff for transient Gemini 503/429 errors
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            result = await agent.ainvoke({"input": user_input})
            return result
        except Exception as e:
            err_msg = str(e).lower()
            is_transient = any(k in err_msg for k in [
                "503", "unavailable", "429", "resource_exhausted",
                "quota", "overloaded", "try again"
            ])
            if is_transient and attempt < max_attempts:
                wait_secs = 5 * attempt  # 5s, 10s
                logger.warning(
                    f"⚠️ [AGENT] Gemini transient error (attempt {attempt}/{max_attempts}): {str(e)[:120]}. "
                    f"Retrying in {wait_secs}s..."
                )
                await asyncio.sleep(wait_secs)
            else:
                raise
