import asyncio
import signal
from typing import List

import structlog

from core.config import settings
from queue_infra.redis_queue import RedisTaskQueue, TaskConsumer
from services.task_processor import TaskProcessor

logger = structlog.get_logger()


class WorkerManager:
    def __init__(self, num_workers: int = None):
        self.num_workers = num_workers or settings.MAX_WORKERS
        self.queue = RedisTaskQueue()
        self.consumers: List[TaskConsumer] = []
        self.running = False

    async def start(self):
        """Start all worker processes"""
        await self.queue.connect()

        # Create consumers with the processor callback
        processor = TaskProcessor(task_queue=self.queue)
        for i in range(self.num_workers):
            consumer = TaskConsumer(
                queue=self.queue,
                worker_id=f"worker-{i}",
                callback=processor.process_task,  # <— clean injection of logic
                batch_size=1,
                max_retries=3,
                dead_letter_queue="dead_letter_tasks",
            )
            self.consumers.append(consumer)

        self.running = True
        logger.info(f"Starting {self.num_workers} workers...")

        # Run all consumers in parallel
        try:
            await asyncio.gather(*(c.start_consuming() for c in self.consumers))
        except asyncio.CancelledError:
            logger.info("Worker tasks cancelled")

    async def stop(self):
        """Stop all workers gracefully"""
        self.running = False
        logger.info("Stopping all workers...")
        await asyncio.gather(*(c.stop_consuming() for c in self.consumers))
        await self.queue.close()
        logger.info("All workers stopped")


async def main():
    manager = WorkerManager()

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(manager.stop()))

    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
