# Workflow: Self-Reflection and Memory Update

Execute this loop WHENEVER you encounter a significant bug, a dependency conflict, or a user corrects your code. This is your in-context reinforcement learning cycle.

## Step 1: Analyze the Failure
1. What was the intended outcome?
2. What was the actual outcome (or error message)?
3. Why did the initial approach fail? (e.g., version mismatch, hardware limitation, async blocking).

## Step 2: Formulate the Rule
Extract a generalized, reusable rule from the specific failure. 
*Poor Rule*: "Use version 2.1 instead of 2.0."
*Good Rule*: "FastAPI Pydantic v2 requires `model_validate` instead of `parse_obj` when deserializing database models."

## Step 3: Update Memory
1. Open `.agent/memory/LESSONS_LEARNED.md`.
2. Append the new rule to the appropriate section using the format:
   - **[Date] Issue**: <brief description> -> **Fix**: <actionable rule>.
3. **CRITICAL**: Do not delete existing memory unless it is explicitly outdated and contradicted by a newer, proven solution.

## Step 4: Update Skills (If Applicable)
If the mistake reveals a fundamental gap in your skill documentation (e.g., a specific Flutter accessibility widget requirement), autonomously edit the relevant `.agent/skills/*.md` file to include the new directive.