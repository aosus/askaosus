import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import urljoin

import aiohttp

from .config import Config
from .responses import ResponseConfig

logger = logging.getLogger(__name__)


@dataclass
class DiscoursePost:
    """Represents a Discourse forum post."""
    id: int
    title: str
    excerpt: str
    url: str
    topic_id: int
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    like_count: int = 0
    reply_count: int = 0


class DiscourseSearcher:
    """Handles searching the Discourse forum for relevant posts."""
    
    def __init__(self, config: Config):
        """Initialize the Discourse searcher."""
        self.config = config
        self.base_url = config.discourse_base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize response configuration
        self.response_config = ResponseConfig()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if not self.session or self.session.closed:
            headers = {
                "User-Agent": "Askaosus Matrix Bot/1.0",
            }
            
            # Add API authentication if available
            if self.config.discourse_api_key and self.config.discourse_username:
                headers["Api-Key"] = self.config.discourse_api_key
                headers["Api-Username"] = self.config.discourse_username
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        
        return self.session
    
    async def search(self, query: str, limit: int = 6) -> List[DiscoursePost]:
        """
        Search Discourse for posts related to the query.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of DiscoursePost objects
        """
        logger.info(f"Searching Discourse for: '{query}' (limit: {limit})")
        results = await self._perform_search(query, limit)
        
        # Fetch limited content for each result (first 1000 chars)
        for post in results:
            try:
                limited_content = await self._fetch_limited_topic_content(post.topic_id, 1000)
                post.excerpt = limited_content
            except Exception as e:
                logger.warning(f"Failed to fetch content for topic {post.topic_id}: {e}")
                # Fallback to existing excerpt
                pass
                
        logger.info(f"Found {len(results)} results")
        return results
    
    def _deduplicate_results(self, results: List[DiscoursePost], seen_topic_ids: Set[int]) -> List[DiscoursePost]:
        """Remove duplicates based on topic ID to ensure each topic appears only once."""
        unique_results = []
        for result in results:
            if result.topic_id not in seen_topic_ids:
                seen_topic_ids.add(result.topic_id)
                unique_results.append(result)
        return unique_results
    
    async def _perform_search(self, query: str, limit: int = 6) -> List[DiscoursePost]:
        """
        Perform a single search request to Discourse.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of DiscoursePost objects
        """
        try:
            session = await self._get_session()
            
            # Prepare search parameters
            search_url = urljoin(self.base_url, "/search.json")
            params = {
                "q": query,
                "order": "relevance",
                "limit": limit,
            }
            
            logger.debug(f"Performing search: {search_url}")
            logger.debug(f"Search query: '{query}'")
            
            async with session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Response keys: {list(data.keys())}")
                    
                    # Log the structure of the response
                    if "posts" in data:
                        logger.debug(f"Found {len(data['posts'])} posts in response")
                    if "topics" in data:
                        logger.debug(f"Found {len(data['topics'])} topics in response")
                    
                    results = self._parse_search_results(data)
                    logger.debug(f"Parsed {len(results)} valid results")
                    
                    return results
                else:
                    response_text = await response.text()
                    logger.warning(f"Search failed with status {response.status}: {response_text}")
                    return []
        
        except Exception as e:
            logger.error(f"Error performing search: {e}", exc_info=True)
            return []
    
    def _parse_search_results(self, data: dict) -> List[DiscoursePost]:
        """Parse Discourse search results into DiscoursePost objects, only including topics."""
        posts = []
        
        try:
            # Only process topics - ignore individual posts/replies
            # This ensures the LLM only receives topic-level results, not individual replies
            if "topics" in data:
                for topic_data in data["topics"]:
                    post = self._parse_topic(topic_data)
                    if post:
                        posts.append(post)
            
            # Preserve relevance order as returned by Discourse API (no manual sorting)
            
        except Exception as e:
            logger.error(f"Error parsing Discourse search results: {e}", exc_info=True)
        
        return posts
    
    def _parse_post(self, post_data: dict) -> Optional[DiscoursePost]:
        """Parse a single post from Discourse API response."""
        try:
            post_id = post_data.get("id")
            topic_id = post_data.get("topic_id")
            
            if not post_id or not topic_id:
                return None
            
            # Get excerpt or content
            excerpt = post_data.get("blurb", "")
            if not excerpt:
                excerpt = post_data.get("excerpt", "")
            if not excerpt:
                # Fallback to content if available
                excerpt = post_data.get("cooked", "")[:300] + "..."
            
            # Construct URL - always point to topic, not specific post
            url = f"{self.base_url}/t/{topic_id}"
            
            return DiscoursePost(
                id=post_id,
                title=post_data.get("topic_title", self.response_config.get_discourse_message("untitled_post")),
                excerpt=excerpt,
                url=url,
                topic_id=topic_id,
                category_id=post_data.get("category_id"),
                created_at=post_data.get("created_at"),
                like_count=post_data.get("like_count", 0),
                reply_count=post_data.get("reply_count", 0),
            )
        
        except Exception as e:
            logger.error(f"Error parsing post: {e}", exc_info=True)
            return None
    
    def _parse_topic(self, topic_data: dict) -> Optional[DiscoursePost]:
        """Parse a topic from Discourse API response as a post."""
        try:
            topic_id = topic_data.get("id")
            
            if not topic_id:
                return None
            
            # Get excerpt
            excerpt = topic_data.get("excerpt", "")
            if not excerpt:
                excerpt = self.response_config.get_discourse_message("default_excerpt")
            
            # Construct URL
            url = f"{self.base_url}/t/{topic_id}"
            
            # Get title and ensure it's not empty
            title = topic_data.get("title") or ""
            title = title.strip()
            if not title:
                title = self.response_config.get_discourse_message("untitled_topic")
            
            return DiscoursePost(
                id=topic_id,
                title=title,
                excerpt=excerpt,
                url=url,
                topic_id=topic_id,
                category_id=topic_data.get("category_id"),
                tags=topic_data.get("tags", []),
                created_at=topic_data.get("created_at"),
                like_count=topic_data.get("like_count", 0),
                reply_count=topic_data.get("posts_count", 0),
            )
        
        except Exception as e:
            logger.error(f"Error parsing topic: {e}", exc_info=True)
            return None
    
    async def _fetch_limited_topic_content(self, topic_id: int, limit: int = 1000) -> str:
        """Fetch limited text content of a topic, strip HTML, return up to specified chars."""
        # Retrieve topic JSON including all posts
        session = await self._get_session()
        topic_url = urljoin(self.base_url, f"/t/{topic_id}.json")
        async with session.get(topic_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to fetch topic {topic_id}: {resp.status}")
            data = await resp.json()

        # Extract and clean post contents
        content_parts = []
        for post in data.get("post_stream", {}).get("posts", []):
            cooked = post.get("cooked", "") or ""
            # Strip HTML tags
            text = re.sub(r'<[^>]+>', '', cooked)
            content_parts.append(text)

        full_text = "\n\n".join(content_parts)
        # Limit to specified characters
        return full_text[:limit]

    async def _fetch_full_topic_content(self, topic_id: int) -> str:
        """Fetch full text content of a topic, strip HTML, return up to 4000 chars."""
        return await self._fetch_limited_topic_content(topic_id, 4000)
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
