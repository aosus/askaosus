import logging
from typing import List

from openai import OpenAI, AsyncOpenAI

from .config import Config
from .discourse import DiscoursePost

logger = logging.getLogger(__name__)


class LLMClient:
    """Handles communication with Language Learning Models."""
    
    def __init__(self, config: Config):
        """Initialize the LLM client."""
        self.config = config
        
        # Initialize OpenAI-compatible client
        client_kwargs = config.get_openai_client_kwargs()
        self.client = AsyncOpenAI(**client_kwargs)
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt from file."""
        try:
            with open("/app/system_prompt.md", "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            # Fallback system prompt
            return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return """أنت مساعد ذكي لمجتمع أسس، المجتمع العربي الأكبر للبرمجيات الحرة والمفتوحة المصدر.

مهمتك هي مساعدة المستخدمين بالإجابة على أسئلتهم بناءً على محتوى المجتمع. 

قواعد الإجابة:
1. اكتب إجابة قصيرة ومفيدة باللغة العربية
2. استند على المحتوى المقدم من المجتمع
3. اذكر رابط المنشور الأكثر صلة للمزيد من التفاصيل
4. شجع المستخدم على زيارة المجتمع للاستفادة أكثر
5. إذا لم تجد إجابة مناسبة، اعتذر ووجه المستخدم لطرح السؤال في المجتمع

احرص على أن تكون الإجابة مختصرة (أقل من 500 كلمة) ومشجعة للمستخدم لزيارة المجتمع."""
    
    async def generate_answer(self, question: str, search_results: List[DiscoursePost]) -> str:
        """
        Generate an answer to a question based on search results.
        
        Args:
            question: The user's question
            search_results: List of relevant Discourse posts
            
        Returns:
            Generated answer
        """
        try:
            # Log the search results first
            logger.info(f"Processing question: {question}")
            logger.info(f"Found {len(search_results)} search results from Discourse")
            
            for i, result in enumerate(search_results):
                logger.debug(f"Result {i+1}: {result.title} - {result.url}")
                logger.debug(f"  Excerpt: {result.excerpt[:200]}...")
            
            # Prepare context from search results
            context = self._prepare_context(search_results)
            logger.debug(f"Prepared context length: {len(context)} characters")
            
            # Prepare messages for the LLM
            user_message = f"""
السؤال: {question}

المحتوى من مجتمع أسس:
{context}

أجب على السؤال باللغة العربية بناءً على المحتوى المقدم. اجعل الإجابة مختصرة ومفيدة، واذكر رابط المنشور الأكثر صلة.
"""
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ]
            # Log the LLM input messages
            logger.info("LLM input messages:")
            for msg in messages:
                logger.info(f"  {msg['role']}: {msg['content']}")
            
            # Log the input to LLM
            logger.info(f"Sending request to LLM provider: {self.config.llm_provider}")
            logger.info(f"Model: {self.config.llm_model}")
            logger.debug(f"System prompt length: {len(self.system_prompt)} characters")
            logger.debug(f"User message length: {len(user_message)} characters")
            
            # Generate response
            response = await self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=messages,
                max_tokens=self.config.llm_max_tokens,
                temperature=self.config.llm_temperature,
            )
            
            # Log the response
            answer = response.choices[0].message.content.strip()
            logger.info(f"LLM response received - length: {len(answer)} characters")
            # Log LLM output
            logger.info(f"LLM output: {answer}")
            logger.debug(f"Raw LLM response: {answer}")
            
            # Log usage if available
            if hasattr(response, 'usage') and response.usage:
                logger.info(f"Token usage - prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens}, total: {response.usage.total_tokens}")
            
            # Add a footer encouraging forum participation
            answer += f"\n\n💬 للمزيد من المناقشات والمساعدة، تفضل بزيارة مجتمع أسس: {self.config.discourse_base_url}"
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return "عذراً، حدث خطأ أثناء توليد الإجابة. يرجى المحاولة مرة أخرى أو زيارة مجتمع أسس مباشرة: https://discourse.aosus.org"
    
    def _prepare_context(self, search_results: List[DiscoursePost]) -> str:
        """Prepare context string from search results."""
        if not search_results:
            return "لا توجد نتائج بحث"
        
        context_parts = []
        for i, post in enumerate(search_results):
            context_parts.append(f"""
المنشور {i+1}:
العنوان: {post.title}
المحتوى: {post.excerpt}
الرابط: {post.url}
عدد الإعجابات: {post.like_count}
عدد الردود: {post.reply_count}
---""")
        
        return "\n".join(context_parts)
