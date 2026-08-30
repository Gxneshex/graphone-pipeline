"""
src/llm/orchestrator.py
A resilient multi-tier LLM data extraction orchestrator. Cascades across 
Gemini, Groq, and DeepSeek, utilizing native structured schemas and an 
automated Pydantic JSON self-correction routine.
"""

import os
import json
import logging
from typing import Type, TypeVar, Optional
from pydantic import BaseModel

# Standard Python SDK client imports for multi-tier fallbacks
from google import genai
from google.genai import types
from groq import Groq

from src.utils.retry import retry_with_backoff

logger = logging.getLogger("graphone-pipeline.orchestrator")
T = TypeVar("T", bound=BaseModel)

class LLMOrchestrator:
    def __init__(self):
        # Configure fallback providers through your environment templates
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        
        # Pull model designations or assign default standard primitives
        self.gemini_model = os.getenv("PRIMARY_LLM_MODEL", "gemini-2.5-flash")
        self.groq_model = os.getenv("FALLBACK_LLM_MODEL", "llama-3.3-70b-versatile")
        self.deepseek_model = "gpt-4o-mini"

    @retry_with_backoff(retries=3, base_delay=2.0, max_delay=15.0, exceptions=(Exception,))
    def _call_gemini_tier(self, prompt: str, target_schema: Type[T]) -> str:
        """Tier 1 Execution: Structured extraction using the recommended Google GenAI client."""
        logger.info(f"Invoking Primary Tier 1 Engine ({self.gemini_model})...")
        # Native client initialization automatically targets the system OPENAI_API_KEY / GEMINI environment variables
        client = genai.Client()
        response = client.models.generate_content(
            model=self.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=target_schema,
                temperature=0.1
            ),
        )
        if not response.text:
            raise ValueError("Empty generation block returned from Gemini API tier.")
        return response.text.strip()

    @retry_with_backoff(retries=3, base_delay=2.0, max_delay=15.0, exceptions=(Exception,))
    def _call_groq_tier(self, prompt: str, target_schema: Type[T]) -> str:
        """Tier 2 Fallback Execution: Structured extraction utilizing Groq Schema Mode."""
        if not self.groq_key:
            raise ValueError("Groq credential token missing from runtime parameters.")
            
        logger.info(f"Cascading to Tier 2 Fallback Engine ({self.groq_model})...")
        client = Groq(api_key=self.groq_key)
        
        # Enforce valid schema generation directly over the Groq REST client API connection
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.groq_model,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": target_schema.__name__,
                    "schema": target_schema.model_json_schema()
                }
            },
            temperature=0.1
        )
        res_text = chat_completion.choices[0].message.content
        if not res_text:
            raise ValueError("Empty completion block returned from Groq API tier.")
        return res_text.strip()

    @retry_with_backoff(retries=3, base_delay=2.0, max_delay=15.0, exceptions=(Exception,))
    def _call_deepseek_tier(self, prompt: str) -> str:
        """Tier 3 Fallback Execution: Standard JSON object generation using OpenAI."""
        logger.info(f"Cascading to Final Tier 3 Fallback Engine ({self.deepseek_model})...")
        if not self.openai_key:
            raise ValueError("OpenAI credential token missing from runtime parameters.")
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_key)
        
        response = client.chat.completions.create(
            model=self.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        res_text = response.choices[0].message.content
        if not res_text:
            raise ValueError("Empty completion block returned from OpenAI API tier.")
        return res_text.strip()

    def _execute_fallback_chain(self, prompt: str, target_schema: Type[T]) -> str:
        """Cascades down the model chain until a raw string block is successfully returned."""
        try:
            return self._call_gemini_tier(prompt, target_schema)
        except Exception as e1:
            logger.warning(f"Primary Gemini infrastructure encountered a failure: {e1}")
            try:
                return self._call_groq_tier(prompt, target_schema)
            except Exception as e2:
                logger.warning(f"Secondary Groq infrastructure encountered a failure: {e2}")
                try:
                    return self._call_deepseek_tier(prompt)
                except Exception as e3:
                    logger.critical(f"All multi-tier LLM fallback components broke permanently: {e3}")
                    raise RuntimeError("Multi-tier extraction engine failed to compute a response block.")

    def extract_structured_data(self, unstructured_text: str, target_schema: Type[T]) -> Optional[T]:
        """
        Transforms messy inputs into canonical Pydantic structures.
        Features an automated self-correction loop to repair schema validation errors.
        """
        base_prompt = (
            f"You are an expert data intelligence agent extraction tool. Your job is to extract unstructured data "
            f"and format it into a valid JSON object matching this schema blueprint: {json.dumps(target_schema.model_json_schema())}.\n"
            f"Raw text chunk payload content:\n{unstructured_text}"
        )

        # Execution Attempt 1: Core extraction pass across our fallback infrastructure channels
        raw_json_string = ""
        try:
            raw_json_string = self._execute_fallback_chain(base_prompt, target_schema)
            return target_schema.model_validate_json(raw_json_string)
            
        except Exception as validation_error:
            # Self-Correction Loop: If Pydantic throws a parsing issue, compile an error correction prompt
            logger.warning(f"Pydantic validation layer rejected the initial JSON string asset: {validation_error}")
            logger.info("Initiating automated self-correction feedback loop session...")
            
            repair_prompt = (
                f"Your previous JSON output failed validation with the following parsing exception error: {str(validation_error)}.\n"
                f"Original schema target rules mapping guidelines: {json.dumps(target_schema.model_json_schema())}.\n"
                f"Incorrect JSON string produced: {raw_json_string}\n"
                f"Analyze the mistake, fix the field shapes, and output only the corrected valid JSON string object block."
            )
            
            try:
                # Re-submit to repaired execution channel logic paths
                repaired_json_string = self._execute_fallback_chain(repair_prompt, target_schema)
                return target_schema.model_validate_json(repaired_json_string)
            except Exception as failure_loop_err:
                logger.error(f"Self-correction loop failed to repair schema formatting rules: {failure_loop_err}")
                return None
