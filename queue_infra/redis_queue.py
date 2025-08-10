import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

import redis.asyncio as redis
import structlog

from core.config import settings
from schemas.task import QueuedTask, TaskPriorityEnum

logger = structlog.get_logger()


class RedisTaskQueue:
    def __init__(self):
        self.redis_client = None
        self.priority_queues = {
            TaskPriorityEnum.HIGH: settings.TASK_QUEUE_HIGH_PRIORITY,
            TaskPriorityEnum.NORMAL: settings.TASK_QUEUE_NORMAL_PRIORITY,
            TaskPriorityEnum.LOW: settings.TASK_QUEUE_LOW_PRIORITY,
        }

    async def connect(self):
        """Initialize Redis connection"""
        self.redis_client = redis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        # Create consumer groups for each priority queue
        for priority, queue_name in self.priority_queues.items():
            try:
                await self.redis_client.xgroup_create(
                    queue_name, settings.CONSUMER_GROUP, id="0", mkstream=True
                )
            except redis.RedisError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(
                        f"Failed to create consumer group for {queue_name}: {e}"
                    )

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    async def enqueue_task(self, task: QueuedTask) -> str:
        """Add task to appropriate priority queue"""
        queue_name = self.priority_queues[task.priority]

        task_data = {
            "task_id": task.task_id,
            "user_id": task.user_id,
            "task_type": task.task_type,
            "priority": task.priority,
            "input_text": task.input_text,
            "user_context": json.dumps(task.user_context),
            "accessibility_mode": str(task.accessibility_mode),
            "webhook_url": task.webhook_url or "",
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "queued_at": datetime.utcnow().isoformat(),
        }

        # Add to Redis stream
        message_id = await self.redis_client.xadd(queue_name, task_data)

        logger.info(
            "Task queued",
            task_id=task.task_id,
            priority=task.priority,
            queue=queue_name,
            message_id=message_id,
        )

        return message_id

    async def get_queue_length(self, priority: TaskPriorityEnum) -> int:
        """Get number of pending tasks in a priority queue"""
        queue_name = self.priority_queues[priority]
        return await self.redis_client.xlen(queue_name)

    async def get_queue_stats(self) -> Dict[str, int]:
        """Get statistics for all queues"""
        stats = {}
        for priority, queue_name in self.priority_queues.items():
            stats[priority] = await self.redis_client.xlen(queue_name)
        return stats


logger = structlog.get_logger()


class TaskConsumer:
    def __init__(
        self,
        queue,
        worker_id: str,
        callback: Callable[[QueuedTask], Awaitable[bool]],
        batch_size: int = 1,
        max_retries: int = 3,
        dead_letter_queue: Optional[str] = None,
    ):
        self.queue = queue
        self.worker_id = worker_id
        self.callback = callback
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.dead_letter_queue = dead_letter_queue
        self.running = False

    async def start_consuming(self):
        """Start consuming tasks from all priority queues"""
        if not self.callback:
            raise ValueError("A callback handler must be provided to TaskConsumer")

        self.running = True
        logger.info(f"Consumer {self.worker_id} started")
        while self.running:
            try:
                # Try high priority first, then normal, then low
                for priority in [
                    TaskPriorityEnum.HIGH,
                    TaskPriorityEnum.NORMAL,
                    TaskPriorityEnum.LOW,
                ]:
                    queue_name = self.queue.priority_queues[priority]

                    messages = await self.queue.redis_client.xreadgroup(
                        settings.CONSUMER_GROUP,
                        self.worker_id,
                        {queue_name: ">"},
                        count=self.batch_size,
                        block=1000,  # 1s timeout
                    )

                    if messages:
                        for stream, msgs in messages:
                            tasks = [
                                self._handle_message(stream, msg_id, fields, priority)
                                for msg_id, fields in msgs
                            ]
                            await asyncio.gather(*tasks)
                        break  # Always check high priority again
            except Exception as e:
                logger.exception("Consumer error")
                await asyncio.sleep(5)  # backoff

        logger.info(f"Consumer {self.worker_id} stopped main loop")

    async def stop_consuming(self):
        """Stop consuming tasks after finishing current batch"""
        logger.info(f"Stopping consumer {self.worker_id}...")
        self.running = False

    async def _handle_message(
        self, stream: str, msg_id: str, fields: Dict, priority: TaskPriorityEnum
    ):
        """Process a single message safely"""
        try:
            task_data = self._deserialize_task(fields)
            logger.info(
                "Processing task",
                task_id=task_data.task_id,
                worker=self.worker_id,
                priority=priority,
            )
            import pdb

            pdb.set_trace()
            success = await self.callback(task_data)

            if success:
                await self.queue.redis_client.xack(
                    stream, settings.CONSUMER_GROUP, msg_id
                )
                logger.info(f"Task {task_data.task_id} completed successfully")
            else:
                await self._handle_failure(task_data, stream, msg_id)

        except Exception as e:
            logger.exception(f"Error processing message {msg_id}")

    async def _handle_failure(self, task_data: QueuedTask, stream: str, msg_id: str):
        """Handle failed task with retry or dead-letter"""
        task_data.retry_count += 1

        if task_data.retry_count <= self.max_retries:
            await self.queue.enqueue_task(task_data, delay=2**task_data.retry_count)
            await self.queue.redis_client.xack(stream, settings.CONSUMER_GROUP, msg_id)
            logger.warning(
                f"Retrying task {task_data.task_id} "
                f"(attempt {task_data.retry_count}/{self.max_retries})"
            )
        else:
            if self.dead_letter_queue:
                await self.queue.enqueue_task(
                    task_data, queue_name=self.dead_letter_queue
                )
                logger.error(f"Task {task_data.task_id} moved to dead-letter queue")
            await self.queue.redis_client.xack(stream, settings.CONSUMER_GROUP, msg_id)

    def _deserialize_task(self, fields: Dict) -> QueuedTask:
        """Convert raw Redis fields into QueuedTask"""
        return QueuedTask(
            task_id=int(fields["task_id"]),
            user_id=int(fields["user_id"]),
            task_type=fields["task_type"],
            priority=fields["priority"],
            input_text=fields["input_text"],
            user_context=json.loads(fields["user_context"]),
            accessibility_mode=fields["accessibility_mode"].lower() == "true",
            webhook_url=fields.get("webhook_url"),
            retry_count=int(fields.get("retry_count", 0)),
            max_retries=int(fields.get("max_retries", self.max_retries)),
        )


# class TaskConsumer:
#     def __init__(self, queue: RedisTaskQueue, worker_id: str, callback=None):
#         self.queue = queue
#         self.worker_id = worker_id
#         self.running = False
#         self.callback = callback

#     async def start_consuming(self):
#         """Start consuming tasks from all priority queues"""
#         self.running = True
#         logger.info(f"Consumer {self.worker_id} started")

#         while self.running:
#             try:
#                 # Try high priority first, then normal, then low
#                 for priority in [TaskPriorityEnum.HIGH, TaskPriorityEnum.NORMAL, TaskPriorityEnum.LOW]:
#                     queue_name = self.queue.priority_queues[priority]

#                     # Read from consumer group
#                     messages = await self.queue.redis_client.xreadgroup(
#                         settings.CONSUMER_GROUP,
#                         self.worker_id,
#                         {queue_name: '>'},
#                         count=1,
#                         block=1000  # 1 second timeout
#                     )

#                     if messages:
#                         for stream, msgs in messages:
#                             for msg_id, fields in msgs:
#                                 await self._process_message(stream, msg_id, fields, priority)
#                         break  # Process one message then check high priority again

#             except Exception as e:
#                 logger.error(f"Consumer error: {e}")
#                 await asyncio.sleep(5)  # Back off on error

#     async def stop_consuming(self):
#         """Stop consuming tasks"""
#         self.running = False
#         logger.info(f"Consumer {self.worker_id} stopped")

#     async def _process_message(self, stream: str, msg_id: str, fields: Dict, priority: TaskPriorityEnum):
#         """Process a single task message"""
#         try:
#             task_data = QueuedTask(
#                 task_id=int(fields["task_id"]),
#                 user_id=int(fields["user_id"]),
#                 task_type=fields["task_type"],
#                 priority=fields["priority"],
#                 input_text=fields["input_text"],
#                 user_context=json.loads(fields["user_context"]),
#                 accessibility_mode=fields["accessibility_mode"].lower() == "true",
#                 webhook_url=fields["webhook_url"] if fields["webhook_url"] else None,
#                 retry_count=int(fields["retry_count"]),
#                 max_retries=int(fields["max_retries"])
#             )

#             logger.info(
#                 "Processing task",
#                 task_id=task_data.task_id,
#                 worker=self.worker_id,
#                 priority=priority
#             )

#             # Import here to avoid circular imports
#             from services.task_processor import TaskProcessor
#             processor = TaskProcessor()

#             # Process the task
#             success = await processor.process_task(task_data)

#             if success:
#                 # Acknowledge successful processing
#                 await self.queue.redis_client.xack(stream, settings.CONSUMER_GROUP, msg_id)
#                 logger.info(f"Task {task_data.task_id} completed successfully")
#             else:
#                 # Handle retry logic
#                 if task_data.retry_count < task_data.max_retries:
#                     await self._retry_task(task_data)
#                     await self.queue.redis_client.xack(stream, settings.CONSUMER_GROUP, msg_id)
#                 else:
#                     logger.error(f"Task {task_data.task_id} failed after {task_data.max_retries} retries")
#                     await self.queue.redis_client.xack(stream, settings.CONSUMER_GROUP, msg_id)

#         except Exception as e:
#             logger.error(f"Error processing message {msg_id}: {e}")
#             # Don't ack failed messages - they'll be retried

#     async def _retry_task(self, task_data: QueuedTask):
#         """Retry a failed task with exponential backoff"""
#         task_data.retry_count += 1

#         # Exponential backoff: 2^retry_count seconds
#         delay = 2 ** task_data.retry_count

#         # Schedule retry (in a real implementation, you might use a delayed queue)
#         await asyncio.sleep(delay)

#         # Re-enqueue with updated retry count
#         await self.queue.enqueue_task(task_data)

#         logger.info(
#             f"Task {task_data.task_id} retried (attempt {task_data.retry_count}/{task_data.max_retries})"
#         )


# import asyncio
# import json
# import structlog
# from typing import Callable, Dict, Optional, Awaitable
# from core.config import settings
# from common.enums import TaskPriorityEnum
# from schemas.task import QueuedTask
