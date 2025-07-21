import asyncio
import logging
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv
# Load .env file without overwriting existing environment variables
load_dotenv(override=False)

from .bot import AskaosusBot
from .config import Config
from .logging_utils import configure_logging

logger = logging.getLogger(__name__)


def signal_handler(bot: AskaosusBot):
    """Handle shutdown signals gracefully by shutting down the bot and stopping the event loop."""
    def handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        # Schedule bot shutdown; sync_forever will exit when client is closed
        asyncio.get_event_loop().create_task(bot.shutdown())
    return handler


async def test_discourse_search(config: Config):
    """Test Discourse search functionality."""
    from .discourse import DiscourseSearcher
    
    searcher = DiscourseSearcher(config)
    
    # Test a single query
    query = "كيف أثبت أوبونتو"
    logger.info(f"Testing search with query: '{query}'")
    results = await searcher.search(query)
    logger.info(f"Found {len(results)} total results for '{query}'")
    
    for i, result in enumerate(results):
        logger.info(f"  {i+1}. {result.title}")
    
    await searcher.close()


async def main():
    """Main entry point for the bot."""
    try:
        # Load configuration
        config = Config()
        
        # Configure logging with our custom setup
        configure_logging(
            log_level=config.log_level,
            logs_dir='/app/logs',
            exclude_matrix_nio=config.exclude_matrix_nio_logs
        )
        
        logger.info("Askaosus Matrix Bot starting up...")
        logger.info(f"Logging configured - level: {config.log_level}, LLM level: {config.llm_log_level}")
        
        # Test Discourse search if in debug mode
        if config.bot_debug:
            logger.info("Debug mode enabled, testing Discourse search...")
            await test_discourse_search(config)
        
        # Create bot instance
        bot = AskaosusBot(config)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler(bot))
        signal.signal(signal.SIGTERM, signal_handler(bot))
        
        # Start the bot
        logger.info("Starting Askaosus Matrix Bot...")
        await bot.start()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("/app/logs").mkdir(exist_ok=True)
    
    # Run the bot
    asyncio.run(main())
