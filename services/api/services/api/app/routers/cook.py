
# --- Helper Endpoint (v15.2) ---

@router.post("/session/{session_id}/help", response_model=CookStepHelpResponse)
async def get_cook_step_help(
    session_id: str,
    payload: CookStepHelpRequest,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered help for a specific cooking step.
    Scope: Workspace.
    """
    return await cook_assist_help.get_step_help(
        db=db,
        session_id=session_id,
        req=payload,
        workspace_id=workspace.id  # Pass UUID not string slug often, but service handles standard
    )
