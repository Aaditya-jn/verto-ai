# main.py
import os
import json
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import httpx
from fastapi import FastAPI, Request
from twilio.rest import Client

from handlers.sandbox_handler import (
    is_activation_message,
    is_language_selection,
    ACTIVATION_REPLY,
    LANGUAGE_CONFIRMED
)
from handlers.media_handler import download_twilio_media, get_media_category
from handlers.reply_formatter import format_english_verdict
from utils.language_store import get_user_language, set_user_language
from contextlib import asynccontextmanager
from utils.logger import log, logger
from agent.deep_agent import run_detector_agent, startup_mcp, shutdown_mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: initialize MCP client once
    await startup_mcp()
    yield
    # shutdown: close MCP client
    await shutdown_mcp()


app = FastAPI(lifespan=lifespan)
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


async def check_url_active(url: str, client: httpx.AsyncClient) -> bool:
    """Verify if a URL is active (returns 2xx or 3xx status)."""
    try:
        # Use HEAD first for speed
        resp = await client.head(url, timeout=2.0, follow_redirects=True)
        if resp.status_code in range(200, 400):
            return True
        # Fallback to GET for servers that block HEAD (like Cloudflare or some media sites)
        resp = await client.get(url, timeout=2.0, follow_redirects=True)
        return resp.status_code in range(200, 400)
    except Exception:
        return False


async def filter_sources_alive(sources: list[str]) -> list[str]:
    """Filter out dead or 404 URLs from the source list in parallel."""
    if not sources or sources == ["No verified source found."]:
        return sources
        
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}) as client:
        tasks = [check_url_active(url, client) for url in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        active_sources = []
        for url, is_alive in zip(sources, results):
            if is_alive is True:
                active_sources.append(url)
                
        if not active_sources:
            return ["No verified source found."]
        return active_sources


def send_whatsapp(to: str, body: str):
    twilio_client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=to,
        body=body
    )


def extract_text_output(output_data) -> str:
    if isinstance(output_data, list):
        if len(output_data) > 0:
            first_item = output_data[0]
            if isinstance(first_item, dict) and "text" in first_item:
                return str(first_item["text"])
            elif hasattr(first_item, "text"):
                return str(first_item.text)
            else:
                return str(first_item)
        return ""
    return str(output_data)


@app.post("/test")
async def test_webhook(request: Request):
    form = await request.form()
    from_number = form.get("From", "")
    send_whatsapp(from_number, "Test reply works! ✅")
    return {"status": "test_ok"}


@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()
    from_number = form.get("From", "")
    body = form.get("Body", "").strip()
    num_media = int(form.get("NumMedia", 0))
    media_url = form.get("MediaUrl0", "")
    media_type = form.get("MediaContentType0", "")

    try:
        import traceback
        log("WEBHOOK_RECEIVED", from_number, f"Body: {body}, Media: {num_media}")
        print(f"🔔 [WEBHOOK] Received from {from_number}: {body[:100]}")
        logger.info("🚀 [AGENT] Starting new analysis workflow")
        log("INCOMING", from_number, body[:100])

        # ── 1. SANDBOX ACTIVATION ──────────────────────────────────────────────────
        if is_activation_message(body):
            send_whatsapp(from_number, ACTIVATION_REPLY)
            log("ACTIVATION", from_number)
            return {"status": "activation_sent"}

        # ── 2. LANGUAGE SELECTION ──────────────────────────────────────────────────
        selected_lang = is_language_selection(body)
        if selected_lang:
            set_user_language(from_number, selected_lang)
            confirmation = LANGUAGE_CONFIRMED.get(selected_lang, f"✅ Language set to {selected_lang}.")
            send_whatsapp(from_number, confirmation)
            log("LANGUAGE_SET", from_number, selected_lang)
            return {"status": "language_set"}

        # ── 3. BUILD AGENT INPUT ───────────────────────────────────────────────────
        if num_media > 0 and media_url:
            category = get_media_category(media_type)
            if category == "audio":
                send_whatsapp(from_number, "⚠️ Audio messages are not supported yet. Please send text, image, video, or PDF.")
                return {"status": "unsupported_media"}
            if category == "unknown":
                send_whatsapp(from_number, "⚠️ Unsupported file type. Please send text, image, video, or PDF.")
                return {"status": "unsupported_media"}

            file_path = download_twilio_media(media_url, media_type)
            logger.info(f"📁 [AGENT] Media received: {file_path}")
            agent_input = f"MEDIA_TYPE:{category} PATH:{file_path} TEXT:{body}"
            log("MEDIA_RECEIVED", from_number, category)
        elif body:
            agent_input = body
            log("TEXT_RECEIVED", from_number, body[:100])
        else:
            send_whatsapp(from_number, "Please send a news headline, image, video, or PDF to fact-check.")
            return {"status": "empty"}

        logger.info(f"📋 [AGENT] Input: [ORIGINAL_USER_CONTENT_START] {body if body else agent_input} [ORIGINAL_USER_CONTENT_END]")
        print(f"🤖 [AGENT] Starting analysis for: {agent_input[:100]}")

        # ── 4. RUN DEEPAGENT ───────────────────────────────────────────────────────
        try:
            result = await asyncio.wait_for(run_detector_agent(agent_input), timeout=90)
            raw_output = extract_text_output(result.get("output", ""))
            print(f"✅ [AGENT] Result: {raw_output}")
        except asyncio.TimeoutError:
            print(f"❌ [AGENT] Timeout error")
            send_whatsapp(from_number, "⚠️ Analysis timed out. Please try again with a shorter news snippet.")
            log("TIMEOUT", from_number)
            return {"status": "timeout"}

        # ── 5. PARSE AGENT OUTPUT ──────────────────────────────────────────────────
        try:
            clean = raw_output.strip().strip("```json").strip("```").strip()
            parsed = json.loads(clean)
            verdict = parsed.get("verdict", "UNVERIFIED")
            logger.info(f"✅ [AGENT] Verdict generated: {verdict}")

            # Verify and filter sources to ensure no 404s are sent
            sources = await filter_sources_alive(parsed.get("sources", []))

            english_reply = format_english_verdict(
                verdict=verdict,
                explanation=parsed.get("explanation", ""),
                evidence=parsed.get("evidence", ""),
                sources=sources,
                confidence=parsed.get("confidence", "Low"),
                hashtags=parsed.get("hashtags", "#FactCheck")
            )
        except Exception:
            english_reply = raw_output if raw_output else "Could not analyze this news. Please try again."
            logger.info("✅ [AGENT] Verdict generated: UNVERIFIED")

        # ── 6. SEND ENGLISH REPLY ──────────────────────────────────────────────────
        print(f"📤 [TWILIO] Sending reply to {from_number}")
        send_whatsapp(from_number, english_reply)
        logger.info(f"📤 [AGENT] Reply sent to {from_number}")
        log("REPLY_SENT_EN", from_number, english_reply[:100])

        # ── 7. TRANSLATE + SEND IN USER LANGUAGE ──────────────────────────────────
        user_lang = get_user_language(from_number)
        if user_lang != "English":
            try:
                translate_result = await asyncio.wait_for(
                    run_detector_agent(f"TRANSLATE_ONLY:{english_reply} TARGET_LANGUAGE:{user_lang}"),
                    timeout=30
                )
                translated = extract_text_output(translate_result.get("output", "")).strip()
                if translated:
                    print(f"📤 [TWILIO] Sending translated reply to {from_number}")
                    send_whatsapp(from_number, translated)
                    logger.info(f"📤 [AGENT] Reply sent to {from_number}")
                    log("REPLY_SENT_TRANSLATED", from_number, user_lang)
            except Exception as e:
                log("TRANSLATE_ERROR", from_number, str(e))

        return {"status": "done"}

    except Exception as e:
        print(f"❌ [ERROR] {str(e)}")
        print(traceback.format_exc())
        log("ERROR", from_number, traceback.format_exc())
        try:
            send_whatsapp(from_number, "⚠️ Something went wrong on the server. Please try again later.")
        except:
            pass # Failsafe
        return {"status": "error"}
