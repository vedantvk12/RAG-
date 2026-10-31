import json
import logging
import httpx
from typing import List, AsyncGenerator
from app.llm.provider import LLMProvider, ChatMessage

logger = logging.getLogger(__name__)

class OpenAILLMProvider(LLMProvider):
    """
    Generic OpenAI-compatible API provider (works for OpenAI, Groq, Together, vLLM, etc.)
    """
    def __init__(
        self, 
        base_url: str, 
        api_key: str, 
        model_name: str, 
        temperature: float = 0.1,
        max_tokens: int = 1000
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens if max_tokens != 1000 else 2500
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate_response(self, messages: List[ChatMessage], **kwargs) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": str(m.content or "")} for m in messages],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                
            if response.status_code != 200:
                logger.error(f"LLM Provider Error: {response.status_code} - {response.text}")
                response.raise_for_status()

            data = response.json()
            if not data.get("choices") or not data["choices"][0].get("message"):
                raise ValueError("Malformed response from LLM provider")
                
            import re
            message = data["choices"][0]["message"]
            content = message.get("content")
            if content is None:
                content = message.get("reasoning") or ""
            
            raw_text = str(content or "")
            try:
                # Remove any <think> tags or reasoning artifacts
                clean_content = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
                if not clean_content and "<think>" in raw_text:
                    clean_content = re.sub(r'</?think>', '', raw_text).strip()
                    
                # If the model wrote a drafting scratchpad ending with the actual answer
                draft_split = re.split(r"(?i)\b(?:let's\s+(?:craft|formulate|write|structure|build|compose|draft)[^\n:]*|final\s+answer|draft\s+response)\s*:\s*", clean_content)
                if len(draft_split) > 1 and draft_split[-1].strip():
                    clean_content = draft_split[-1].strip().strip('"').strip("'")
                    
                # If the model appended trailing meta-commentary after the response (e.g., 'Cite Source 3...', 'We have Source 2...')
                clean_content = re.sub(r'\n\n(?i)(?:Cite\s+Source|We\s+have\s+Source|We\'ll\s+cite|Thus\s+we\s+can\s+state).*$', '', clean_content, flags=re.DOTALL).strip()
                            
                # Normalize fullwidth brackets if model emitted them
                clean_content = re.sub(r'【\s*(?:Source\s+)?(\d+)\s*】', r'[Source \1]', clean_content)
                clean_content = clean_content.replace('【', '[').replace('】', ']')
                
                return clean_content or raw_text
            except Exception as pe:
                logger.warning(f"Error during response post-processing: {pe}")
                return raw_text
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from LLM: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM Provider error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Network error communicating with LLM: {e}")
            raise Exception("Failed to connect to LLM Provider.") from e
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}", exc_info=True)
            raise

    async def stream_response(self, messages: List[ChatMessage], **kwargs) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", url, headers=self.headers, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"LLM Stream Error: {response.status_code} - {error_text.decode('utf-8')}")
                        raise Exception("LLM Provider returned an error during streaming.")
                        
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            data_str = line[6:]
                            try:
                                chunk = json.loads(data_str)
                                if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                                    yield chunk["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            logger.error(f"Error during LLM streaming: {e}")
            raise Exception("Streaming from LLM Provider failed.")
