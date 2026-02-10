import os
import json
import logging
import asyncio
from typing import List, Optional
from openai import AsyncOpenAI
import google.generativeai as genai
from main import extract_article

# Configure logger
logger = logging.getLogger(__name__)

# Optimized Prompt: English instructions for better adherence by small models (Gemma/Llama)
from newsroom_rules import GUJARATI_NEWSROOM_PROMPT


class ArticleGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "llama3",
    ):
        self.api_key = api_key or "ollama"
        self.base_url = base_url or os.getenv(
            "LLM_BASE_URL", "http://localhost:11434/v1"
        )
        self.model = model or os.getenv("LLM_MODEL", "llama3")
        self.client = AsyncOpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=1200.0
        )

    async def _generate_with_gemini(self, keypoints, context_text, api_key, model_name):
        """Helper to generate using Google Gemini with auto-fallback"""
        try:
            if not api_key:
                return {"success": False, "error": "Gemini API Key Required"}

            genai.configure(api_key=api_key)

            # 1. Define Prompt
            prompt = f"""{GUJARATI_NEWSROOM_PROMPT}

SOURCE DATA:
Keypoints: {keypoints}

Source Material:
{context_text[:20000] if context_text else "No source provided"}

INSTRUCTION: 
Based on the SOURCE DATA, write a news report in GUJARATI following the EDITORIAL RULES.
Return purely JSON."""

            # 2. Define Generation Logic
            async def try_generate(m_name):
                logger.info(f"Attempting generation with model: {m_name}")
                model = genai.GenerativeModel(m_name)
                loop = asyncio.get_event_loop()
                # Run sync call in thread
                response = await loop.run_in_executor(
                    None,
                    lambda: model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"},
                    ),
                )
                return response.text

            # 3. Try requested model first
            try:
                result_text = await try_generate(model_name)
                logger.info(f"Success with {model_name}")
                return self._parse_response(result_text)
            except Exception as e:
                logger.warning(f"Failed with {model_name}: {e}")

                # 4. Auto-discovery of working models
                logger.info("Auto-discovering available Gemini models...")
                loop = asyncio.get_event_loop()

                try:
                    available_models = await loop.run_in_executor(
                        None, genai.list_models
                    )
                    candidates = []
                    for m in available_models:
                        if "generateContent" in m.supported_generation_methods:
                            # Prefer 'pro' or 'flash' models
                            name = m.name.replace("models/", "")
                            if "gemini" in name:
                                candidates.append(name)

                    logger.info(f"Found candidate models: {candidates}")

                    # Sort candidates to prefer stable/pro models if possible
                    # Prioritize: gemini-1.5-flash (most likely to work), then pro
                    candidates.sort(key=lambda x: 0 if "flash" in x else 1)

                    for candidate in candidates:
                        if candidate == model_name:
                            continue

                        try:
                            logger.info(f"Fallback attempt with: {candidate}")
                            result_text = await try_generate(candidate)
                            return self._parse_response(result_text)
                        except Exception as inner_e:
                            logger.warning(f"Fallback {candidate} failed: {inner_e}")
                            continue

                    # If we get here, all failed
                    raise Exception("All available Gemini models failed.")

                except Exception as list_e:
                    logger.error(f"Model listing failed: {list_e}")
                    raise e  # Raise original error if listing fails

        except Exception as e:
            logger.error(f"Gemini Generation Error: {str(e)}")
            return {"success": False, "error": f"Gemini Error: {str(e)}"}

    def _parse_response(self, result_text):
        """Helper to parse JSON response with regex fallback"""
        import re

        # Clean up markdown code blocks
        clean_text = result_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            # First try standard JSON parsing
            result_json = json.loads(clean_text)
            if not result_json.get("title"):
                result_json["title"] = "સમાચાર શીર્ષક"
            if not result_json.get("content"):
                result_json["content"] = "<p>સામગ્રી જનરેટ કરવામાં નિષ્ફળ.</p>"
            return {"success": True, **result_json}

        except json.JSONDecodeError as je:
            logger.warning(f"JSON Parse Error: {je}. Attempting regex fallback.")

            # Regex Fallback strategy
            title_match = re.search(
                r'"title"\s*:\s*"(.*?)(?<!\\)"', clean_text, re.DOTALL
            )
            content_match = re.search(
                r'"content"\s*:\s*"(.*?)(?<!\\)"', clean_text, re.DOTALL
            )

            if title_match or content_match:
                title = title_match.group(1) if title_match else "શીર્ષક ઉપલબ્ધ નથી"
                content = content_match.group(1) if content_match else ""

                # Cleanup escaped characters
                title = title.replace('\\"', '"').strip()
                content = content.replace('\\"', '"').replace("\\n", " ").strip()

                if not content:
                    # If regex failed to find content, use the whole text if it looks like article text
                    # Remove the title part if found
                    fallback_text = clean_text
                    if title_match:
                        fallback_text = fallback_text.replace(title_match.group(0), "")
                    content = fallback_text.strip(' {}",')

                # Ensure HTML paragraph tags
                if not content.startswith("<p"):
                    paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
                    content = "".join([f"<p>{p}</p>" for p in paragraphs])

                return {
                    "success": True,
                    "title": title,
                    "content": content,
                    "warning": "Parsed via Regex",
                }

            # If all else fails, return raw output nicely formatted
            return {
                "success": True,
                "title": "જનરેટેડ આર્ટિકલ (Raw Output)",
                "content": f"<div style='white-space: pre-wrap; word-break: break-word; font-family: monospace; font-size: 0.8rem; background: #f5f5f5; padding: 1rem; border-radius: 0.5rem;'>{clean_text}</div>",
                "warning": "JSON Parse Error",
            }

    async def generate_article_from_text(
        self, keypoints, context_text, api_key=None, base_url=None, model=None
    ):
        eff_model = model or self.model

        # Check for Gemini
        if eff_model and "gemini" in eff_model.lower():
            return await self._generate_with_gemini(
                keypoints, context_text, api_key, eff_model
            )

        # OLLAMA / OPENAI Logic
        if len(context_text) > 3000:
            context_text = context_text[:3000] + "... [TRUNCATED]"

        eff_base_url = base_url or self.base_url
        eff_api_key = api_key or self.api_key or "ollama"

        client = getattr(self, "client", None)
        is_custom_req = (api_key and api_key != self.api_key) or (
            base_url and base_url != self.base_url
        )

        if is_custom_req or not client:
            client = AsyncOpenAI(
                api_key=eff_api_key, base_url=eff_base_url, timeout=1200.0
            )

        user_prompt = f"""SOURCE DATA:
Keypoints: {keypoints}
Source Material: {context_text[:3000] if context_text else "No source provided"}

INSTRUCTION: 
Write a news report in GUJARATI following the EDITORIAL RULES.
Return ONLY VALID JSON in the specified format."""

        try:
            response = await client.chat.completions.create(
                model=eff_model,
                messages=[
                    {"role": "system", "content": GUJARATI_NEWSROOM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=800,
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception as e:
            return {"success": False, "error": f"LLM Generation Error: {str(e)}"}

    async def generate_article(
        self, keypoints, source_urls, api_key=None, base_url=None, model=None
    ):
        scraped_texts = []
        for url in source_urls:
            try:
                content = await asyncio.to_thread(extract_article, url)
                if content:
                    scraped_texts.append(content)
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")

        combined_text = "\n\n".join(scraped_texts) if scraped_texts else ""
        return await self.generate_article_from_text(
            keypoints=keypoints,
            context_text=combined_text,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
