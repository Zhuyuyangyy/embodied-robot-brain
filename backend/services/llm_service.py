"""
LLM服务 - 支持多Provider、重试、超时降级fallback
工业级：tenacity retry（3次指数退避）+ timeout(30s) + fallback降级
"""
import asyncio
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from httpx import TimeoutException as HttpxTimeoutException

from core.config import settings
from core.metrics import LLM_CALL_COUNT, LLM_CALL_LATENCY, LLM_TOKEN_USAGE

from loguru import logger


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    tokens_used: int
    latency_ms: float
    fallback_used: bool = False


class LLMService:
    """
    LLM服务：支持Claude/GPT-4，自动重试+超时降级
    工业级重试策略：3次指数退避 + 30s超时 + fallback降级
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT  # 30s
        self.max_retries = 3

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        fallback: bool = True,
    ) -> LLMResponse:
        """
        生成文本，支持重试和fallback
        使用tenacity实现指数退避重试
        """
        start_time = time.perf_counter()
        last_error = None

        # Primary + fallback providers chain
        providers = [self.provider] if not fallback else [self.provider, "openai", "mock"]
        if fallback and self.provider == "openai":
            providers = ["openai", "anthropic", "mock"]
        elif fallback and self.provider == "anthropic":
            providers = ["anthropic", "openai", "mock"]

        for attempt, prov in enumerate(providers):
            try:
                result = await self._call_provider_with_timeout(
                    prov, prompt, system, max_tokens or settings.LLM_MAX_TOKENS, temperature
                )
                result.latency_ms = (time.perf_counter() - start_time) * 1000
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"LLM provider {prov} failed (attempt {attempt+1}/{len(providers)}): {e}")
                if attempt < len(providers) - 1:
                    # Exponential backoff: 0.5s, 1s, 2s...
                    await asyncio.sleep(0.5 * (2 ** attempt))

        # Ultimate fallback to mock
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(f"All LLM providers failed, using mock fallback: {last_error}")
        return LLMResponse(
            content=f"[模拟响应] 基于提示生成: {prompt[:100]}...",
            provider="mock",
            model="mock-model",
            tokens_used=50,
            latency_ms=latency_ms,
            fallback_used=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
        retry=retry_if_exception_type((Exception, HttpxTimeoutException)),
        reraise=True,
    )
    async def _call_provider_with_timeout(
        self,
        provider: str,
        prompt: str,
        system: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """调用具体的LLM provider，带重试和30s超时"""
        if provider == "anthropic":
            return await self._call_anthropic(prompt, system, max_tokens, temperature)
        elif provider == "openai":
            return await self._call_openai(prompt, system, max_tokens, temperature)
        else:
            raise Exception(f"Unknown provider: {provider}")

    async def _call_anthropic(
        self, prompt: str, system: Optional[str], max_tokens: int, temperature: float
    ) -> LLMResponse:
        """调用Anthropic Claude"""
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise Exception("ANTHROPIC_API_KEY not configured")

        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=api_key)

            messages = [{"role": "user", "content": prompt}]
            resp = await asyncio.wait_for(
                client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=messages,
                ),
                timeout=self.timeout,
            )

            LLM_CALL_COUNT.labels(provider="anthropic", model="claude-sonnet-4-20250514", status="success").inc()
            LLM_CALL_LATENCY.labels(provider="anthropic", model="claude-sonnet-4-20250514").observe(time.perf_counter())
            LLM_TOKEN_USAGE.labels(provider="anthropic", model="claude-sonnet-4-20250514", token_type="output").inc(resp.usage.output_tokens)
            LLM_TOKEN_USAGE.labels(provider="anthropic", model="claude-sonnet-4-20250514", token_type="input").inc(resp.usage.input_tokens)

            return LLMResponse(
                content=resp.content[0].text,
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                tokens_used=resp.usage.input_tokens + resp.usage.output_tokens,
                latency_ms=0,
            )
        except asyncio.TimeoutError:
            LLM_CALL_COUNT.labels(provider="anthropic", model="claude-sonnet-4-20250514", status="timeout").inc()
            raise Exception("Anthropic API timeout")
        except Exception as e:
            LLM_CALL_COUNT.labels(provider="anthropic", model="claude-sonnet-4-20250514", status="error").inc()
            raise

    async def _call_openai(
        self, prompt: str, system: Optional[str], max_tokens: int, temperature: float
    ) -> LLMResponse:
        """调用OpenAI GPT-4"""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise Exception("OPENAI_API_KEY not configured")

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ),
                timeout=self.timeout,
            )

            LLM_CALL_COUNT.labels(provider="openai", model="gpt-4o", status="success").inc()
            usage = resp.usage
            LLM_TOKEN_USAGE.labels(provider="openai", model="gpt-4o", token_type="total").inc(usage.total_tokens)

            return LLMResponse(
                content=resp.choices[0].message.content,
                provider="openai",
                model="gpt-4o",
                tokens_used=usage.total_tokens,
                latency_ms=0,
            )
        except asyncio.TimeoutError:
            LLM_CALL_COUNT.labels(provider="openai", model="gpt-4o", status="timeout").inc()
            raise Exception("OpenAI API timeout")
        except Exception as e:
            LLM_CALL_COUNT.labels(provider="openai", model="gpt-4o", status="error").inc()
            raise


# Global singleton
llm_service = LLMService()
