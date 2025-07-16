import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import urljoin

import aiohttp

from .config import Config

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
        
        # Common Arabic to English software name mappings
        self.name_mappings = {
            # Operating Systems
            "أوبونتو": ["ubuntu", "أوبونتو"],
            "لينكس": ["linux", "لينكس"],
            "وندوز": ["windows", "وندوز"],
            "فيدورا": ["fedora", "فيدورا"],
            "دبيان": ["debian", "دبيان"],
            "أرش": ["arch", "أرش"],
            "منت": ["mint", "منت"],
            "سنتوس": ["centos", "سنتوس"],
            "ريد هات": ["redhat", "rhel", "ريد هات"],
            "أوبن سوزي": ["opensuse", "suse", "أوبن سوزي"],
            
            # Desktop Environments
            "جنوم": ["gnome", "جنوم"],
            "كي دي إي": ["kde", "plasma", "كي دي إي"],
            "إكس إف سي إي": ["xfce", "إكس إف سي إي"],
            "سينامون": ["cinnamon", "سينامون"],
            "ميت": ["mate", "ميت"],
            
            # Applications
            "فايرفوكس": ["firefox", "فايرفوكس"],
            "كروم": ["chrome", "chromium", "كروم"],
            "ليبر أوفيس": ["libreoffice", "ليبر أوفيس"],
            "جيمب": ["gimp", "جيمب"],
            "في إل سي": ["vlc", "في إل سي"],
            "بلندر": ["blender", "بلندر"],
            "إنكسكيب": ["inkscape", "إنكسكيب"],
            "أوداسيتي": ["audacity", "أوداسيتي"],
            "كودي": ["kodi", "كودي"],
            "سبوتيفاي": ["spotify", "سبوتيفاي"],
            "ديسكورد": ["discord", "ديسكورد"],
            "تيليجرام": ["telegram", "تيليجرام"],
            "سكايب": ["skype", "سكايب"],
            "زووم": ["zoom", "زووم"],
            
            # Development Tools
            "فيسوال ستوديو كود": ["vscode", "visual studio code", "code", "فيسوال ستوديو كود"],
            "سابليم تكست": ["sublime", "sublime text", "سابليم تكست"],
            "أتوم": ["atom", "أتوم"],
            "إيماكس": ["emacs", "إيماكس"],
            "فيم": ["vim", "neovim", "فيم"],
            "جيت": ["git", "github", "gitlab", "جيت"],
            "دوكر": ["docker", "دوكر"],
            "كوبرنتيس": ["kubernetes", "k8s", "كوبرنتيس"],
            "أباتشي": ["apache", "httpd", "أباتشي"],
            "إنجين إكس": ["nginx", "إنجين إكس"],
            
            # Programming Languages
            "بايثون": ["python", "بايثون"],
            "جافا": ["java", "جافا"],
            "جافا سكريبت": ["javascript", "js", "nodejs", "node", "جافا سكريبت"],
            "سي": ["c", "سي"],
            "سي بلس بلس": ["c++", "cpp", "سي بلس بلس"],
            "سي شارب": ["c#", "csharp", "dotnet", "سي شارب"],
            "بي إتش بي": ["php", "بي إتش بي"],
            "روبي": ["ruby", "روبي"],
            "جو": ["go", "golang", "جو"],
            "رست": ["rust", "رست"],
            "سويفت": ["swift", "سويفت"],
            "كوتلن": ["kotlin", "كوتلن"],
            
            # Common terms
            "تثبيت": ["install", "installation", "setup", "تثبيت"],
            "إزالة": ["remove", "uninstall", "delete", "إزالة"],
            "تحديث": ["update", "upgrade", "patch", "تحديث"],
            "مشكلة": ["problem", "issue", "error", "bug", "مشكلة"],
            "خطأ": ["error", "exception", "crash", "خطأ"],
            "حل": ["solution", "fix", "solve", "resolve", "حل"],
            "إعداد": ["setup", "configuration", "config", "settings", "إعداد"],
            "شرح": ["tutorial", "guide", "explanation", "how-to", "شرح"],
            "مساعدة": ["help", "support", "assistance", "مساعدة"],
            "أداء": ["performance", "speed", "optimization", "أداء"],
            "حماية": ["security", "protection", "firewall", "حماية"],
            "شبكة": ["network", "internet", "wifi", "ethernet", "شبكة"],
            "قاعدة بيانات": ["database", "mysql", "postgresql", "sqlite", "قاعدة بيانات"],
            "خادم": ["server", "hosting", "cloud", "خادم"],
            "نسخ احتياطي": ["backup", "restore", "نسخ احتياطي"],
        }
    
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
    
    async def search(self, query: str) -> List[DiscoursePost]:
        """
        Search Discourse for posts related to the query using multiple strategies.
        
        Args:
            query: The search query
            
        Returns:
            List of DiscoursePost objects (deduplicated)
        """
        all_results = []
        seen_topic_ids = set()
        
        # Strategy 1: Original query
        logger.info(f"Search strategy 1: Original query - '{query}'")
        results = await self._perform_search(query)
        all_results.extend(self._deduplicate_results(results, seen_topic_ids))
        
        # Strategy 2: Extract keywords and search with them
        keywords = self._extract_keywords(query)
        if keywords:
            keyword_query = " ".join(keywords)
            logger.info(f"Search strategy 2: Keywords - '{keyword_query}'")
            results = await self._perform_search(keyword_query)
            all_results.extend(self._deduplicate_results(results, seen_topic_ids))
        
        # Strategy 3: Search with English equivalents of Arabic terms
        english_terms = self._get_english_equivalents(query)
        if english_terms:
            english_query = " ".join(english_terms)
            logger.info(f"Search strategy 3: English equivalents - '{english_query}'")
            results = await self._perform_search(english_query)
            all_results.extend(self._deduplicate_results(results, seen_topic_ids))
        
        # Strategy 4: Search with individual important terms
        important_terms = self._extract_important_terms(query)
        for term in important_terms[:2]:  # Limit to top 2 terms to avoid too many requests
            logger.info(f"Search strategy 4: Individual term - '{term}'")
            results = await self._perform_search(term)
            all_results.extend(self._deduplicate_results(results, seen_topic_ids))
        
        # Preserve relevance order as returned by Discourse API (no manual sorting)
        
        # Return top results
        final_results = all_results[:self.config.bot_max_search_results]
        logger.info(f"Total unique results found: {len(final_results)}")
        
        return final_results
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from the query."""
        # Remove common Arabic stop words
        stop_words = {
            "في", "من", "إلى", "على", "مع", "عن", "كيف", "ماذا", "متى", "أين", "لماذا",
            "هل", "ما", "هو", "هي", "هذا", "هذه", "التي", "الذي", "التي", "والتي",
            "أن", "إن", "كان", "كانت", "يكون", "تكون", "لكي", "حتى", "لا", "لم", "لن"
        }
        
        # Split query into words and filter
        words = re.findall(r'\b\w+\b', query)
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return keywords[:5]  # Return top 5 keywords
    
    def _get_english_equivalents(self, query: str) -> List[str]:
        """Get English equivalents for Arabic terms in the query."""
        english_terms = []
        query_lower = query.lower()
        
        for arabic_term, equivalents in self.name_mappings.items():
            if arabic_term in query_lower:
                english_terms.extend(equivalents)
        
        return list(set(english_terms))  # Remove duplicates
    
    def _extract_important_terms(self, query: str) -> List[str]:
        """Extract the most important terms for individual searches."""
        # Look for software names, technical terms, etc.
        important_patterns = [
            r'\b[A-Za-z]+\b',  # English words
            r'\b\w{4,}\b',     # Words with 4+ characters
        ]
        
        terms = []
        for pattern in important_patterns:
            matches = re.findall(pattern, query)
            terms.extend(matches)
        
        # Also add any mapped terms
        for arabic_term in self.name_mappings.keys():
            if arabic_term in query.lower():
                terms.append(arabic_term)
        
        # Remove duplicates and sort by length (longer terms first)
        unique_terms = list(set(terms))
        unique_terms.sort(key=len, reverse=True)
        
        return unique_terms[:3]  # Return top 3 most important terms
    
    def _deduplicate_results(self, results: List[DiscoursePost], seen_topic_ids: Set[int]) -> List[DiscoursePost]:
        """Remove duplicates based on topic ID to ensure each topic appears only once."""
        unique_results = []
        for result in results:
            if result.topic_id not in seen_topic_ids:
                seen_topic_ids.add(result.topic_id)
                unique_results.append(result)
        return unique_results
    
    async def _perform_search(self, query: str) -> List[DiscoursePost]:
        """
        Perform a single search request to Discourse.
        
        Args:
            query: The search query
            
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
                # Increase limit for individual searches since we'll deduplicate
                "limit": min(10, self.config.bot_max_search_results * 2),
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
                title=post_data.get("topic_title", "منشور بدون عنوان"),
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
                excerpt = "موضوع في مجتمع أسس"
            
            # Construct URL
            url = f"{self.base_url}/t/{topic_id}"
            
            return DiscoursePost(
                id=topic_id,
                title=topic_data.get("title", "موضوع بدون عنوان"),
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
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
