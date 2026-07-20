import asyncio
import logging

logger = logging.getLogger(__name__)

async def send_message_with_retry(send_func, *args, retries=3, delay=1.5, **kwargs):
    """
    Executes a message sending coroutine function (like message.answer or bot.send_message)
    with retry logic in case of network glitches or connection resets on hosting platforms.
    Falls back to plain text if Markdown formatting entity parsing fails.
    """
    for attempt in range(1, retries + 1):
        try:
            return await send_func(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            if ("can't parse entities" in err_str or "bad request" in err_str or "entity" in err_str) and "parse_mode" in kwargs:
                kwargs_no_pm = kwargs.copy()
                kwargs_no_pm.pop("parse_mode", None)
                try:
                    return await send_func(*args, **kwargs_no_pm)
                except Exception as inner_e:
                    logger.warning(f"Fallback without parse_mode failed: {inner_e}")
            logger.warning(f"Attempt {attempt}/{retries} to send message failed: {e}")
            if attempt == retries:
                raise e
            await asyncio.sleep(delay * attempt)
