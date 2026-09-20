# Multi-Agent Learning Support Review

Educational use case: a governance specialist reviews learner data, resource quality, assessment evidence, accessibility, and safeguarding before a personalized learning plan is recommended.

This project uses **Nebius through LangChain** to inspect a learner profile, search educational controls, read governance evidence, and produce actionable conditions for student and educator support. It is designed to be one specialist in a larger workflow with learner-needs, resource-quality, assessment, and recommendation agents.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add NEBIUS_API_KEY
python main.py
```

## Production Pattern Demonstrated

- Policy-grounded learning-support review
- Learner privacy, accessibility, and safeguarding checks
- Risk register as typed JSON
- Governance remediation suggestions
- Conditional support decision
