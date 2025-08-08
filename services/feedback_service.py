import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ai_providers.router import AIProviderRouter
from database.postgres.models.feedback import Feedback
from database.postgres.models.task import Task
from database.postgres.models.user import User


class FeedbackService:
    def __init__(self, ai_router: AIProviderRouter):
        self.ai_router = ai_router
        self.feedback_patterns = {}  # Store learning patterns

    async def process_feedback(
        self, feedback_data: Dict[str, Any], db: Session
    ) -> Dict[str, Any]:
        """Process user feedback and learn from it"""
        try:
            # Create feedback record
            feedback = Feedback(
                user_id=feedback_data["user_id"],
                task_id=feedback_data.get("task_id"),
                feedback_type=feedback_data["feedback_type"],
                rating=feedback_data.get("rating"),
                comment=feedback_data.get("comment"),
                accessibility_issue=feedback_data.get("accessibility_issue"),
                improvement_suggestion=feedback_data.get("improvement_suggestion"),
            )

            db.add(feedback)
            db.commit()
            db.refresh(feedback)

            # Process feedback for learning
            if feedback_data.get("rating", 0) < 3:  # Poor rating
                await self._analyze_failure_feedback(feedback, db)

            # Update accessibility patterns
            if feedback_data.get("accessibility_issue"):
                await self._update_accessibility_patterns(feedback, db)

            return {
                "success": True,
                "feedback_id": feedback.id,
                "message": "Thank you for your feedback. I'll use this to improve.",
                "learned_improvements": await self._get_improvement_suggestions(
                    feedback_data
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process feedback",
            }

    async def _analyze_failure_feedback(self, feedback: Feedback, db: Session):
        """Analyze failed tasks to improve future performance"""
        if not feedback.task_id:
            return

        task = db.query(Task).filter(Task.id == feedback.task_id).first()
        if not task:
            return

        # Use AI to analyze what went wrong
        analysis_prompt = f"""
        Analyze this failed task and feedback:
        
        Task Type: {task.task_type}
        User Input: {task.input_text}
        Error: {task.error_message or 'Unknown'}
        User Feedback: {feedback.comment}
        Rating: {feedback.rating}
        
        Identify:
        1. What went wrong
        2. How to prevent this in the future
        3. Better prompts or validation needed
        
        Return JSON with improvement suggestions.
        """

        try:
            analysis = await self.ai_router.process_with_fallback(
                "generate_response", analysis_prompt
            )

            # Store analysis for future improvements
            self.feedback_patterns[f"{task.task_type}_failures"] = analysis

        except Exception as e:
            print(f"Failed to analyze feedback: {e}")

    async def _update_accessibility_patterns(self, feedback: Feedback, db: Session):
        """Update accessibility support patterns"""
        user = db.query(User).filter(User.id == feedback.user_id).first()
        if not user:
            return

        # Store accessibility patterns per disability type
        disability_key = user.disability_type or "general"

        if disability_key not in self.feedback_patterns:
            self.feedback_patterns[disability_key] = {"issues": [], "solutions": []}

        self.feedback_patterns[disability_key]["issues"].append(
            feedback.accessibility_issue
        )

        if feedback.improvement_suggestion:
            self.feedback_patterns[disability_key]["solutions"].append(
                feedback.improvement_suggestion
            )

    async def _get_improvement_suggestions(
        self, feedback_data: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions based on feedback"""
        suggestions = []

        if feedback_data.get("accessibility_issue"):
            suggestions.append(
                "Added accessibility consideration for future similar requests"
            )

        if feedback_data.get("rating", 0) < 3:
            suggestions.append(
                "Will provide more detailed explanations in similar situations"
            )

        if feedback_data.get("improvement_suggestion"):
            suggestions.append("Your suggestion has been noted for system improvements")

        return suggestions

    async def get_accessibility_guidance(
        self, user_disability: str, task_type: str
    ) -> Dict[str, Any]:
        """Provide accessibility guidance based on learned patterns"""
        disability_patterns = self.feedback_patterns.get(user_disability, {})

        guidance = {
            "accessibility_tips": [],
            "common_issues": [],
            "recommended_approach": None,
        }

        if "issues" in disability_patterns:
            guidance["common_issues"] = disability_patterns["issues"][
                -5:
            ]  # Last 5 issues

        if "solutions" in disability_patterns:
            guidance["accessibility_tips"] = disability_patterns["solutions"][
                -5:
            ]  # Last 5 solutions

        # Generate AI-powered guidance
        if user_disability and task_type:
            prompt = f"""
            Provide accessibility guidance for a user with {user_disability} 
            performing a {task_type} task. Focus on:
            1. Clear communication strategies
            2. Step-by-step guidance
            3. Error prevention
            4. Alternative interaction methods
            """

            try:
                ai_guidance = await self.ai_router.process_with_fallback(
                    "generate_response", prompt
                )
                guidance["recommended_approach"] = ai_guidance
            except Exception:
                guidance["recommended_approach"] = (
                    "Provide clear, step-by-step instructions with confirmation at each step."
                )

        return guidance
