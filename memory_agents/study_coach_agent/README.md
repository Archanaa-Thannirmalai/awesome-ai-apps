### AI Study Coach with Memori & LangGraph

This project implements the concept of an intelligent multi-agent learning ecosystem in which autonomous agents collaborate to improve teaching and learning outcomes. The system identifies learner needs, detects student misconceptions, generates personalized learning resources, evaluates understanding, analyzes learning performance, and provides actionable recommendations to both students and educators.

- **Plans & tracks** learning journeys via a Streamlit UI.
- Uses **LangGraph** to generate quizzes, assess student understanding, and identify misconceptions.
- Produces **personalized learning resources** and targeted study recommendations.
- Stores **structured learner profiles and study sessions in Memori** (SQLite/Postgres/MySQL/MongoDB, configurable).
- Provides a **Memori-powered coaching experience** for progress analysis and educator-ready insights.

#### Three aligned workflow examples

1. **Student misconception detection example** – surfaces gaps in understanding and pinpoints likely misconceptions.
2. **Secure agent control workflow** – keeps agent actions controlled, logged, and safely scoped for an authenticated learning environment.
3. **Collaborative agent review workflow** – lets educators and the learner review AI-generated insights before finalizing recommendations.

---

### Features

- 🧭 **Study Plan tab**
  - Capture a structured learner profile:
    - Name / handle
    - Main goal (e.g. “Pass AWS SAA”, “Master LangGraph”)
    - Timeframe
    - Subjects / topics
    - Weekly study hours
    - Preferred formats (videos, docs, practice problems, etc.)
  - Profile is saved into **Memori** as a tagged JSON document and automatically reused across sessions.

- 📅 **Today’s Session tab**
  - Log each study session:
    - Topic, duration, resource type, perceived difficulty, mood, notes.
  - Runs a **LangGraph-powered verification flow**:
    - Generates 3–5 quiz questions.
    - Prompts you to explain the topic “in your own words”.
    - Detects likely misconceptions and learning gaps.
    - Recommends personalized learning resources and next actions for both the learner and educator.
    - Evaluates understanding (0–100), surfaces feedback, and suggests a next step.
  - Writes a summarised study session into **Memori** (topic, score, misconceptions, recommendations, performance summary).

- 📈 **Progress & Memory tab (chat)**
  - Chat with a Memori-backed assistant about your learning history:
    - “What are my weakest topics right now?”
    - “When do I usually perform best?”
    - “Do I learn better from videos or practice problems?”
  - Uses the same Memori store that holds your profile + session summaries.

- ⚙️ **CockroachDB storage**
  - Uses **CockroachDB** via a Postgres+psycopg SQLAlchemy URL stored in `MEMORI_DB_URL`, e.g.  
    `postgresql+psycopg://user:password@host:26257/database`

---

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- `OPENAI_API_KEY` (Memori registers this OpenAI client)
- `MEMORI_DB_URL` – CockroachDB URL (`postgresql+psycopg://...`)
- `MEMORI_API_KEY` for Memori advanced augmentation / quotas

---

### Install & Run

From the repo root:

```bash
cd memory_agents/study_coach_agent
uv sync
```

Create a `.env` file:

```bash
OPENAI_API_KEY=your_openai_key_here
MEMORI_DB_URL=postgresql+psycopg://user:password@host:26257/database
MEMORI_API_KEY=your_memori_key_here
```

Run the app:

```bash
uv run streamlit run app.py
```

Or with plain pip:

```bash
pip install -e .
streamlit run app.py
```

## License

See the main repository LICENSE file.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

Made with ❤️ by [Studio1](https://www.Studio1hq.com) Team
