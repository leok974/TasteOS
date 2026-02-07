import json
import uuid
import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from ..models import CookSession, Recipe, RecipeStep
from ..schemas import AutoflowRequest, AutoflowResponse, AutoflowSuggestion, AutoflowAction
from ..core.ai_client import ai_client

logger = logging.getLogger(__name__)

class CookAutoflowService:
    def __init__(self):
        self.ai = ai_client
        # Simple in-memory cache: {session_id_step_version: (response, expiry_ts)}
        self._cache = {}

    async def get_next_best_action(
        self, 
        session: CookSession, 
        recipe: Recipe, 
        req: AutoflowRequest
    ) -> AutoflowResponse:
        
        # 1. Check Cache
        cache_key = f"{session.id}_{req.step_index}_{session.state_version}_{req.client_state.active_timer_ids}"
        if cache_key in self._cache:
            resp, expiry = self._cache[cache_key]
            if datetime.now() < expiry:
                return resp

        # 2. Gather Context
        current_step = next((s for s in recipe.steps if s.step_index == req.step_index), None)
        if not current_step:
            return AutoflowResponse(suggestions=[], source="heuristic", autoflow_id=str(uuid.uuid4()))

        # 3. Apply Heuristics (Fast & Safe)
        suggestions = self._apply_heuristics(session, current_step, req)

        # 4. If heuristics are insufficient or mode is 'deep', consult AI
        # For now, we mix both or prefer heuristics for speed unless empty
        source = "heuristic"
        if not suggestions and req.mode == "deep":
            # Optional: Call AI here if heuristics fail
            pass 
        
        # 5. Build Response
        response = AutoflowResponse(
            suggestions=suggestions,
            source=source,
            autoflow_id=str(uuid.uuid4())
        )

        # 6. Cache Response (Short TTL: 30s)
        self._cache[cache_key] = (response, datetime.now() + timedelta(seconds=30))
        
        return response

    def _apply_heuristics(
        self, 
        session: CookSession, 
        step: RecipeStep, 
        req: AutoflowRequest
    ) -> list[AutoflowSuggestion]:
        suggestions = []
        
        # Parse Bullet State
        # step.bullets is a list of strings. 
        # req.client_state.checked_keys contains "s{step_index}.b{bullet_index}"
        total_bullets = len(step.bullets) if step.bullets else 0
        checked_count = 0
        for i in range(total_bullets):
            key = f"s{step.step_index}.b{i}"
            if key in req.client_state.checked_keys:
                checked_count += 1
        
        all_bullets_checked = (total_bullets > 0 and checked_count == total_bullets)
        any_bullets_checked = (checked_count > 0)

        # Timer Logic
        # Rule: Suggest starting timer when:
        # - current step has minutes_est >= 3
        # - AND there is no running timer created for this step
        # - AND user has checked at least one bullet OR "started_step_at" exists (proxy: any_bullets_checked)
        
        has_est_time = step.minutes_est and step.minutes_est >= 3
        
        # Check active timers for this step
        # active_timer_ids in request is just a list of IDs. We need to check session state.
        # Ideally we trust the server session state for timer details, not just client
        step_timers = [
            t for t in session.timers.values() 
            if t.get('step_index') == step.step_index and t.get('state') in ('running', 'paused')
        ]
        completed_step_timers = [
            t for t in session.timers.values() 
            if t.get('step_index') == step.step_index and t.get('state') == 'finished'
        ]
        
        has_running_timer = len(step_timers) > 0
        has_finished_timer = len(completed_step_timers) > 0

        # Suggest Timer
        if has_est_time and not has_running_timer and not has_finished_timer:
            if any_bullets_checked:
                suggestions.append(AutoflowSuggestion(
                    type="start_timer",
                    label=f"Start {step.minutes_est} min timer",
                    action=AutoflowAction(
                        op="create_timer",
                        payload={"minutes": step.minutes_est, "label": step.title, "step_index": step.step_index}
                    ),
                    confidence="high",
                    why="Step has a duration and you've started tasks."
                ))

        # Suggest Completion
        # Rule: Don’t suggest “Mark step complete” unless:
        # - all bullets checked for that step 
        # - AND (either a timer is done (if step minutes_est present) OR user explicitly pressed “Done” (captured elsewhere) OR no timer needed)
        
        timer_requirement_met = True
        if has_est_time:
            # If it needed a timer, we expect one to be finished
            if not has_finished_timer:
                timer_requirement_met = False
        
        if all_bullets_checked and timer_requirement_met:
             suggestions.append(AutoflowSuggestion(
                type="complete_step",
                label="Mark step complete",
                action=AutoflowAction(
                    op="navigate_step",
                    payload={"step_index": step.step_index + 1}
                ),
                confidence="high",
                why="All tasks done and timers finished."
            ))
        
        # If timer is running: "Continue / Prep Next"
        if has_running_timer:
             suggestions.append(AutoflowSuggestion(
                type="prep_next",
                label="Review next step while waiting",
                action=AutoflowAction(
                    op="none", # Just a UI hint or maybe peek
                    payload={}
                ),
                confidence="medium",
                why="Timer is running."
            ))

        return suggestions

cook_autoflow = CookAutoflowService()
