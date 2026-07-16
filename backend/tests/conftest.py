import os
# Force development environment for all pytest runs
os.environ["ENVIRONMENT"] = "development"

# Suppress CrewAI's first-execution "view your traces?" stdin prompt (crewai/events/
# listeners/tracing/utils.py) — it blocks on input() with only a 20s timeout, which
# would otherwise hang the very first Crew/Flow kickoff in any fresh CI runner.
os.environ["CREWAI_TESTING"] = "true"
