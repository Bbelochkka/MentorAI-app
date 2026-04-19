from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

import httpx

from .config import settings


logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    pass


class OllamaProvider:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_json(self, prompt: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
            },
        }

        timeout = httpx.Timeout(
            connect=20.0,
            read=self.timeout_seconds,
            write=60.0,
            pool=60.0,
        )

        last_exc: Exception | None = None
        for attempt in range(1, 3):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, json=payload)

                    if response.status_code >= 400:
                        logger.error("Ollama error status=%s body=%s", response.status_code, response.text)
                        raise LLMProviderError(
                            f"Ошибка запроса к Ollama: status={response.status_code}, body={response.text}"
                        )

                    data = response.json()
                    break
            except httpx.ReadTimeout as exc:
                last_exc = exc
                logger.warning("Ollama timeout on attempt %s/%s", attempt, 2)
                if attempt == 2:
                    raise LLMProviderError(
                        "Ошибка запроса к Ollama: timed out. Попробуйте уменьшить объём контекста или увеличить LLM_TIMEOUT_SECONDS."
                    ) from exc
            except Exception as exc:
                logger.exception("Ошибка запроса к Ollama")
                raise LLMProviderError(f"Ошибка запроса к Ollama: {exc}") from exc
        else:
            raise LLMProviderError(f"Ошибка запроса к Ollama: {last_exc}")

        raw_response = data.get("response")
        if not raw_response:
            raise LLMProviderError("LLM не вернула поле response")

        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            logger.exception("Ollama вернула невалидный JSON")
            raise LLMProviderError(f"Ollama вернула невалидный JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise LLMProviderError("Ollama вернула JSON не в формате объекта")

        return parsed


class GigaChatProvider:
    def __init__(
        self,
        auth_key: str,
        scope: str,
        oauth_url: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 180,
    ) -> None:
        self.auth_key = auth_key.strip()
        self.scope = scope
        self.oauth_url = oauth_url.rstrip("/")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def _build_basic_auth_header(self) -> str:
        if self.auth_key.startswith("Basic "):
            return self.auth_key
        return f"Basic {self.auth_key}"

    def _get_access_token(self) -> str:
        now = time.time()

        if self._access_token and now < self._expires_at - 30:
            return self._access_token

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": self._build_basic_auth_header(),
        }

        data = {
            "scope": self.scope,
        }

        try:
            timeout = httpx.Timeout(
                connect=20.0,
                read=60.0,
                write=60.0,
                pool=60.0,
            )
            with httpx.Client(timeout=timeout) as client:
                response = client.post(self.oauth_url, headers=headers, data=data)

                if response.status_code >= 400:
                    logger.error("GigaChat OAuth error status=%s body=%s", response.status_code, response.text)
                    raise LLMProviderError(
                        f"Ошибка получения токена GigaChat: status={response.status_code}, body={response.text}"
                    )

                payload = response.json()
        except Exception as exc:
            logger.exception("Ошибка получения токена GigaChat")
            raise LLMProviderError(f"Ошибка получения токена GigaChat: {exc}") from exc

        access_token = payload.get("access_token")
        expires_at = payload.get("expires_at")

        if not access_token or not expires_at:
            raise LLMProviderError(f"GigaChat OAuth вернул неожиданный ответ: {payload}")

        self._access_token = access_token
        self._expires_at = float(expires_at)

        return access_token

    def _chat(self, messages: list[dict[str, str]], temperature: float = 0.1) -> str:
        token = self._get_access_token()
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": messages,
        }

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(
            connect=20.0,
            read=self.timeout_seconds,
            write=60.0,
            pool=60.0,
        )

        last_exc: Exception | None = None
        for attempt in range(1, 3):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, headers=headers, json=payload)

                    if response.status_code >= 400:
                        logger.error("GigaChat error status=%s body=%s", response.status_code, response.text)
                        raise LLMProviderError(
                            f"Ошибка запроса к GigaChat: status={response.status_code}, body={response.text}"
                        )

                    data = response.json()
                    break
            except httpx.ReadTimeout as exc:
                last_exc = exc
                logger.warning("GigaChat timeout on attempt %s/%s", attempt, 2)
                if attempt == 2:
                    raise LLMProviderError(
                        "Ошибка запроса к GigaChat: timed out. Попробуйте уменьшить объём контекста или увеличить LLM_TIMEOUT_SECONDS."
                    ) from exc
            except Exception as exc:
                logger.exception("Ошибка запроса к GigaChat")
                raise LLMProviderError(f"Ошибка запроса к GigaChat: {exc}") from exc
        else:
            raise LLMProviderError(f"Ошибка запроса к GigaChat: {last_exc}")

        try:
            raw_response = data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.exception("GigaChat вернула неожиданный ответ")
            raise LLMProviderError(f"GigaChat вернула неожиданный ответ: {data}") from exc

        logger.info("GigaChat raw response (first 2000 chars): %s", raw_response[:2000])
        return raw_response

    @staticmethod
    def _extract_json_candidate(raw_text: str) -> str:
        text = raw_text.strip()

        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()

        start = text.find("{")
        if start == -1:
            return text.strip()

        in_string = False
        escaped = False
        depth = 0
        end: int | None = None

        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = idx
                    break

        if end is not None:
            return text[start:end + 1].strip()

        return text[start:].strip()

    @staticmethod
    def _light_json_repair(text: str) -> str:
        repaired = text.strip()
        repaired = repaired.replace("﻿", "")
        repaired = repaired.replace("“", '"').replace("”", '"').replace("„", '"')
        repaired = repaired.replace("’", "'").replace("`", '"')

        repaired = re.sub(r"//.*?$", "", repaired, flags=re.MULTILINE)
        repaired = re.sub(r"/\*.*?\*/", "", repaired, flags=re.DOTALL)

        repaired = re.sub(
            r'([\{\[,]\s*)([A-Za-zА-Яа-я_][A-Za-zА-Яа-я0-9_\- ]*)(\s*:)',
            lambda m: f'{m.group(1)}"{m.group(2).strip()}"{m.group(3)}',
            repaired,
        )

        repaired = re.sub(
            r'("|\]|\}|\btrue\b|\bfalse\b|\bnull\b|\d)\s*\n\s*(".*?"\s*:)',
            r'\1,\n\2',
            repaired,
            flags=re.IGNORECASE,
        )
        repaired = re.sub(
            r'("|\]|\}|\btrue\b|\bfalse\b|\bnull\b|\d)\s+(".*?"\s*:)',
            r'\1, \2',
            repaired,
            flags=re.IGNORECASE,
        )

        repaired = re.sub(r"(\}|\])\s*(\{)", r"\1, \2", repaired)
        repaired = re.sub(r"(\}|\])\s*(\[)", r"\1, \2", repaired)

        repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)

        open_curly = repaired.count("{")
        close_curly = repaired.count("}")
        if open_curly > close_curly:
            repaired += "}" * (open_curly - close_curly)

        open_square = repaired.count("[")
        close_square = repaired.count("]")
        if open_square > close_square:
            repaired += "]" * (open_square - close_square)

        return repaired

    @staticmethod
    def _try_parse_python_literal(text: str) -> dict[str, Any] | None:
        import ast

        python_like = re.sub(r"\btrue\b", "True", text, flags=re.IGNORECASE)
        python_like = re.sub(r"\bfalse\b", "False", python_like, flags=re.IGNORECASE)
        python_like = re.sub(r"\bnull\b", "None", python_like, flags=re.IGNORECASE)

        try:
            parsed = ast.literal_eval(python_like)
        except Exception:
            return None

        if isinstance(parsed, dict):
            return parsed
        return None

    def _repair_json_via_model(self, broken_response: str) -> dict[str, Any]:
        repair_prompt = f"""
Ниже находится НЕВАЛИДНЫЙ JSON.
Твоя задача — вернуть ТОТ ЖЕ САМЫЙ объект, сохранив смысл и структуру, но в виде строго валидного JSON.

Правила:
1. Верни только JSON.
2. Не добавляй markdown.
3. Не добавляй пояснения.
4. Не меняй смысл, не сокращай и не дополняй данные.
5. Исправь только синтаксис JSON.

Невалидный JSON:
{broken_response}
""".strip()

        repaired_raw = self._chat(
            [
                {
                    "role": "system",
                    "content": "Ты исправляешь синтаксис JSON. Возвращай только валидный JSON.",
                },
                {
                    "role": "user",
                    "content": repair_prompt,
                },
            ],
            temperature=0.0,
        )

        candidate = self._extract_json_candidate(repaired_raw)

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            repaired_candidate = self._light_json_repair(candidate)
            try:
                parsed = json.loads(repaired_candidate)
            except json.JSONDecodeError as exc:
                literal_parsed = self._try_parse_python_literal(repaired_candidate)
                if literal_parsed is not None:
                    return literal_parsed
                raise LLMProviderError(f"GigaChat не смогла корректно починить JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise LLMProviderError("GigaChat после repair-pass вернула JSON не в формате объекта")

        return parsed

    def generate_json(self, prompt: str) -> dict[str, Any]:
        raw_response = self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Ты генератор учебных курсов. "
                        "Отвечай только валидным JSON без markdown и пояснений."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
        )

        candidate = self._extract_json_candidate(raw_response)

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        repaired_candidate = self._light_json_repair(candidate)
        try:
            parsed = json.loads(repaired_candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            literal_parsed = self._try_parse_python_literal(repaired_candidate)
            if literal_parsed is not None:
                return literal_parsed

        logger.warning("GigaChat вернула невалидный JSON, запускаем repair-pass")
        return self._repair_json_via_model(raw_response)


def get_llm_provider():
    provider = settings.llm_provider.lower()

    if provider == "gigachat":
        return GigaChatProvider(
            auth_key=settings.gigachat_auth_key,
            scope=settings.gigachat_scope,
            oauth_url=settings.gigachat_oauth_url,
            base_url=settings.gigachat_base_url,
            model=settings.gigachat_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    if provider == "ollama":
        return OllamaProvider(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    raise LLMProviderError(f"Неизвестный LLM_PROVIDER: {settings.llm_provider}")
