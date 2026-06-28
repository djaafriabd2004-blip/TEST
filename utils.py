import asyncio
import logging

logger = logging.getLogger(__name__)

async def send_message_with_retry(send_func, *args, retries=3, delay=1.5, **kwargs):
    """
    Executes a message sending coroutine function (like message.answer or bot.send_message)
    with retry logic in case of network glitches or connection resets on hosting platforms.
    """
    for attempt in range(1, retries + 1):
        try:
            return await send_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{retries} to send message failed: {e}")
            if attempt == retries:
                raise e
            await asyncio.sleep(delay * attempt)
