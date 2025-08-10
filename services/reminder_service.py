import asyncio
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

import structlog
from models import Reminder, User
from sqlalchemy.orm import Session

from database import SessionLocal
from services.webhook_service import WebhookService

logger = structlog.get_logger()


class ReminderService:
    def __init__(self):
        self.webhook_service = WebhookService()
        self.running = False

    async def start_reminder_checker(self):
        """Start the background reminder checking process"""
        self.running = True
        logger.info("Reminder service started")

        while self.running:
            try:
                await self._check_and_send_reminders()
                await asyncio.sleep(settings.REMINDER_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Reminder service error: {e}")
                await asyncio.sleep(60)  # Back off on error

    async def stop_reminder_checker(self):
        """Stop the reminder checking process"""
        self.running = False
        logger.info("Reminder service stopped")

    async def _check_and_send_reminders(self):
        """Check for due reminders and send them"""
        db = SessionLocal()
        try:
            now = datetime.utcnow()

            # Find reminders that are due
            due_reminders = (
                db.query(Reminder)
                .filter(Reminder.is_active == True, Reminder.next_reminder_at <= now)
                .all()
            )

            for reminder in due_reminders:
                try:
                    await self._send_reminder(reminder, db)
                    await self._schedule_next_reminder(reminder, db)
                except Exception as e:
                    logger.error(f"Failed to process reminder {reminder.id}: {e}")

            db.commit()

        finally:
            db.close()

    async def _send_reminder(self, reminder: Reminder, db: Session):
        """Send a reminder notification"""
        user = db.query(User).filter(User.id == reminder.user_id).first()
        if not user:
            logger.error(f"User not found for reminder {reminder.id}")
            return

        # Determine webhook URL (reminder-specific or user's default)
        webhook_url = reminder.webhook_url or user.webhook_url

        if webhook_url:
            reminder_data = {
                "reminder_id": reminder.id,
                "user_id": reminder.user_id,
                "title": reminder.title,
                "message": reminder.message,
                "reminder_type": reminder.reminder_type,
            }

            success = await self.webhook_service.send_reminder_webhook(
                webhook_url, reminder_data
            )

            if success:
                reminder.last_sent_at = datetime.utcnow()
                logger.info(f"Reminder {reminder.id} sent successfully")
            else:
                logger.error(f"Failed to send reminder {reminder.id}")
        else:
            logger.warning(f"No webhook URL configured for reminder {reminder.id}")

    async def _schedule_next_reminder(self, reminder: Reminder, db: Session):
        """Calculate and set the next reminder time"""
        try:
            next_time = self._parse_schedule_pattern(
                reminder.schedule_pattern, reminder.next_reminder_at
            )
            if next_time:
                reminder.next_reminder_at = next_time
                logger.debug(
                    f"Next reminder for {reminder.id} scheduled at {next_time}"
                )
            else:
                # Invalid pattern or one-time reminder
                reminder.is_active = False
                logger.info(
                    f"Reminder {reminder.id} deactivated (one-time or invalid pattern)"
                )
        except Exception as e:
            logger.error(f"Failed to schedule next reminder for {reminder.id}: {e}")
            reminder.is_active = False

    def _parse_schedule_pattern(self, pattern: str, current_time: datetime) -> datetime:
        """Parse schedule pattern and return next execution time"""
        now = datetime.utcnow()

        # Simple patterns
        if pattern == "daily":
            return current_time + timedelta(days=1)

        if pattern.startswith("daily_at_"):
            time_str = pattern.replace("daily_at_", "")
            try:
                hour, minute = map(int, time_str.split(":"))
                next_day = now.replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                if next_day <= now:
                    next_day += timedelta(days=1)
                return next_day
            except ValueError:
                return None

        if pattern.startswith("every_") and pattern.endswith("_hours"):
            hours = int(pattern.replace("every_", "").replace("_hours", ""))
            return current_time + timedelta(hours=hours)

        if pattern.startswith("every_") and pattern.endswith("_minutes"):
            minutes = int(pattern.replace("every_", "").replace("_minutes", ""))
            return current_time + timedelta(minutes=minutes)

        # Weekly patterns
        if pattern.startswith("weekly_"):
            # e.g., "weekly_monday_09:00"
            parts = pattern.split("_")
            if len(parts) >= 3:
                day_name = parts[1].lower()
                time_str = parts[2]

                days_of_week = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }

                if day_name in days_of_week:
                    try:
                        hour, minute = map(int, time_str.split(":"))
                        target_weekday = days_of_week[day_name]

                        # Calculate next occurrence of this weekday
                        days_ahead = target_weekday - now.weekday()
                        if days_ahead <= 0:  # Target day already happened this week
                            days_ahead += 7

                        next_time = now + timedelta(days=days_ahead)
                        next_time = next_time.replace(
                            hour=hour, minute=minute, second=0, microsecond=0
                        )
                        return next_time
                    except ValueError:
                        return None

        # One-time patterns
        if pattern == "once":
            return None  # Deactivate after first execution

        # Default: treat as one-time
        logger.warning(f"Unknown schedule pattern: {pattern}")
        return None

    async def create_reminder(
        self, reminder_data: Dict[str, Any], db: Session
    ) -> Dict[str, Any]:
        """Create a new reminder"""
        try:
            # Parse initial schedule
            next_time = self._parse_schedule_pattern(
                reminder_data["schedule_pattern"], datetime.utcnow()
            )

            if not next_time and reminder_data["schedule_pattern"] != "once":
                return {
                    "success": False,
                    "error": f"Invalid schedule pattern: {reminder_data['schedule_pattern']}",
                    "supported_patterns": [
                        "daily",
                        "daily_at_HH:MM",
                        "every_N_hours",
                        "every_N_minutes",
                        "weekly_DAYNAME_HH:MM",
                        "once",
                    ],
                }

            reminder = Reminder(
                user_id=reminder_data["user_id"],
                reminder_type=reminder_data["reminder_type"],
                title=reminder_data["title"],
                message=reminder_data["message"],
                schedule_pattern=reminder_data["schedule_pattern"],
                next_reminder_at=next_time or datetime.utcnow(),
                webhook_url=reminder_data.get("webhook_url"),
            )

            db.add(reminder)
            db.commit()
            db.refresh(reminder)

            logger.info(f"Reminder created: {reminder.id}")

            return {
                "success": True,
                "reminder_id": reminder.id,
                "next_reminder_at": (
                    reminder.next_reminder_at.isoformat()
                    if reminder.next_reminder_at
                    else None
                ),
                "message": f"Reminder '{reminder.title}' created successfully",
            }

        except Exception as e:
            logger.error(f"Failed to create reminder: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create reminder",
            }
