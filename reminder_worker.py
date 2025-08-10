import asyncio
import signal

import structlog

from services.reminder_service import ReminderService

logger = structlog.get_logger()


async def main():
    """Main reminder worker process"""
    reminder_service = ReminderService()

    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down reminder service...")
        asyncio.create_task(reminder_service.stop_reminder_checker())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await reminder_service.start_reminder_checker()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await reminder_service.stop_reminder_checker()


if __name__ == "__main__":
    asyncio.run(main())
