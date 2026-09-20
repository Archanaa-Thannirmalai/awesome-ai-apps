from typing import TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


class LearnerProfile(BaseModel):
    name: str = Field(..., description="Learner's name or handle.")
    main_goal: str = Field(..., description="Overall study goal (e.g. pass an exam).")
    timeframe: str = Field(
        ..., description="Time horizon for the goal (e.g. 3 months)."
    )
    subjects: list[str] = Field(default_factory=list, description="Subjects or topics.")
    weekly_hours: int = Field(..., ge=1, le=80, description="Planned hours per week.")
    preferred_formats: list[str] = Field(
        default_factory=list, description="e.g. 'videos', 'docs', 'practice problems'."
    )


class StudyLog(BaseModel):
    topic: str
    duration_minutes: int = Field(..., ge=5, le=600)
    resource_type: str = Field(
        ..., description="e.g. 'video', 'article', 'course', 'problems'."
    )
    perceived_difficulty: str = Field(
        ..., description="Learner's rating, e.g. 'easy', 'medium', 'hard'."
    )
    mood: str | None = Field(
        default=None, description="Optional mood/motivation description."
    )
    free_notes: str | None = None


class QuizQuestion(BaseModel):
    question: str
    type: str = Field(
        default="short_answer", description="short_answer or multiple_choice."
    )
    options: list[str] | None = None


class VerificationResult(BaseModel):
    quiz: list[QuizQuestion]
    explanation_prompt: str
    score: int | None = None
    feedback: str | None = None
    next_step_recommendation: str | None = None
    misconceptions: list[str] = Field(default_factory=list)
    personalized_learning_resources: list[str] = Field(default_factory=list)
    student_recommendations: list[str] = Field(default_factory=list)
    educator_recommendations: list[str] = Field(default_factory=list)
    performance_summary: str | None = None


class VerificationState(TypedDict, total=False):
    profile: LearnerProfile
    log: StudyLog
    quiz: list[QuizQuestion]
    explanation_prompt: str
    user_quiz_answers: list[str]
    user_explanation: str
    score: int
    feedback: str
    next_step_recommendation: str
    misconceptions: list[str]
    personalized_learning_resources: list[str]
    student_recommendations: list[str]
    educator_recommendations: list[str]
    performance_summary: str


def _generate_quiz_node(state: VerificationState, llm_client) -> VerificationState:
    profile = state["profile"]
    log = state["log"]

    system_prompt = (
        "You are an AI study coach. Given a topic and learner context, "
        "write 3-5 focused quiz questions that test real understanding, "
        "not rote memorization."
    )
    user_prompt = (
        f"Learner goal: {profile.main_goal} over {profile.timeframe}\n"
        f"Subjects: {', '.join(profile.subjects) or 'N/A'}\n"
        f"Today's topic: {log.topic}\n"
        f"Perceived difficulty: {log.perceived_difficulty}\n\n"
        "Return the quiz as a numbered list of short-answer questions only."
    )
    response = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content or ""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    questions: list[QuizQuestion] = []
    for line in lines:
        # Strip leading numbering if present
        if line[0].isdigit():
            # e.g. "1. Question"
            parts = line.split(".", 1)
            if len(parts) == 2:
                line = parts[1].strip()
        questions.append(QuizQuestion(question=line))

    if not questions:
        questions = [
            QuizQuestion(
                question=f"Explain the key ideas you learned today about {log.topic}."
            )
        ]

    explanation_prompt = (
        f"In a few paragraphs, explain in your own words what you learned today "
        f"about {log.topic}. Focus on intuition and why things work, not just formulas."
    )

    state["quiz"] = questions
    state["explanation_prompt"] = explanation_prompt
    return state


def _evaluate_node(state: VerificationState, llm_client) -> VerificationState:
    profile = state["profile"]
    log = state["log"]
    questions = state.get("quiz", [])
    answers = state.get("user_quiz_answers", [])
    explanation = state.get("user_explanation", "")

    qa_pairs = []
    for i, q in enumerate(questions):
        ans = answers[i] if i < len(answers) else ""
        qa_pairs.append(f"Q{i + 1}: {q.question}\nA{i + 1}: {ans}")
    qa_text = "\n\n".join(qa_pairs)

    system_prompt = (
        "You are an expert tutor and learning analytics coach. Given the learner's goal, "
        "topic, quiz answers, and reflection, evaluate understanding on a 0-100 scale. "
        "Identify misconceptions, explain why the learner may be struggling, suggest "
        "personalized practice resources, and provide actionable recommendations for both "
        "the student and the educator."
    )
    user_prompt = (
        f"Learner goal: {profile.main_goal} over {profile.timeframe}\n"
        f"Today's topic: {log.topic}\n\n"
        f"Quiz and answers:\n{qa_text}\n\n"
        f"Learner's explanation:\n{explanation}\n\n"
        "1) Provide a single integer score from 0 to 100.\n"
        "2) Detect likely misconceptions and learning gaps.\n"
        "3) Recommend 2-4 personalized learning resources or activities.\n"
        "4) Provide short student-facing recommendations.\n"
        "5) Provide short educator-facing recommendations.\n"
        "6) Summarize the learner's current performance pattern in one sentence.\n"
        "Respond ONLY with valid JSON in the form: "
        '{"score": <int>, "feedback": "<text>", "next_step": "<text>", '
        '"misconceptions": ["<text>"], "personalized_learning_resources": ["<text>"], '
        '"student_recommendations": ["<text>"], "educator_recommendations": ["<text>"], '
        '"performance_summary": "<text>"}'
    )

    # Request structured JSON so we don't have to do fragile brace-slicing.
    response = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content or "{}"

    # Parse strict JSON output into our typed verification state.
    score = 0
    feedback = ""
    next_step = ""
    misconceptions: list[str] = []
    personalized_learning_resources: list[str] = []
    student_recommendations: list[str] = []
    educator_recommendations: list[str] = []
    performance_summary = ""
    try:
        import json  # local import to keep top neat

        obj = json.loads(raw)
        score = int(obj.get("score", 0))
        feedback = str(obj.get("feedback", "") or "")
        next_step = str(obj.get("next_step", "") or "")
        misconceptions = [
            str(item) for item in obj.get("misconceptions", []) if str(item).strip()
        ]
        personalized_learning_resources = [
            str(item)
            for item in obj.get("personalized_learning_resources", [])
            if str(item).strip()
        ]
        student_recommendations = [
            str(item)
            for item in obj.get("student_recommendations", [])
            if str(item).strip()
        ]
        educator_recommendations = [
            str(item)
            for item in obj.get("educator_recommendations", [])
            if str(item).strip()
        ]
        performance_summary = str(obj.get("performance_summary", "") or "")
    except Exception:
        # Fall back to treating the raw content as feedback if parsing somehow fails.
        feedback = raw
        next_step = ""

    state["score"] = score
    state["feedback"] = feedback
    state["next_step_recommendation"] = next_step
    state["misconceptions"] = misconceptions
    state["personalized_learning_resources"] = personalized_learning_resources
    state["student_recommendations"] = student_recommendations
    state["educator_recommendations"] = educator_recommendations
    state["performance_summary"] = performance_summary
    return state


def build_verification_graph(llm_client):
    """
    Build a very small LangGraph graph with two nodes:
    - generate_quiz
    - evaluate (called after the UI has collected answers)
    The UI will typically:
      1) Run generate_quiz
      2) Show quiz & explanation prompt, collect user responses
      3) Re-run graph with answers to execute evaluate
    """
    graph = StateGraph(VerificationState)  # type: ignore[invalid-argument-type]

    def generate_quiz(state: VerificationState) -> VerificationState:
        return _generate_quiz_node(state, llm_client)

    def evaluate(state: VerificationState) -> VerificationState:
        return _evaluate_node(state, llm_client)

    graph.add_node("generate_quiz", generate_quiz)
    graph.add_node("evaluate", evaluate)

    graph.set_entry_point("generate_quiz")
    graph.add_edge("generate_quiz", "evaluate")
    graph.add_edge("evaluate", END)

    return graph.compile()


def run_initial_verification(
    profile: LearnerProfile, log: StudyLog, llm_client
) -> VerificationResult:
    """
    Convenience helper for step 1:
    - Given profile and log, generate quiz + explanation prompt.
    - Do NOT evaluate yet (no answers).
    """
    graph = build_verification_graph(llm_client)
    init_state: VerificationState = {
        "profile": profile,
        "log": log,
        "user_quiz_answers": [],
        "user_explanation": "",
    }
    result_state = graph.invoke(init_state, config={"run_evaluation": False})
    return VerificationResult(
        quiz=result_state["quiz"],
        explanation_prompt=result_state["explanation_prompt"],
    )


def run_full_evaluation(
    profile: LearnerProfile,
    log: StudyLog,
    user_quiz_answers: list[str],
    user_explanation: str,
    llm_client,
) -> VerificationResult:
    """
    Step 2:
    - Take user answers + explanation and run full graph (including evaluation).
    """
    graph = build_verification_graph(llm_client)
    init_state: VerificationState = {
        "profile": profile,
        "log": log,
        "user_quiz_answers": user_quiz_answers,
        "user_explanation": user_explanation,
    }
    result_state = graph.invoke(init_state)
    return VerificationResult(
        quiz=result_state["quiz"],
        explanation_prompt=result_state["explanation_prompt"],
        score=result_state.get("score"),
        feedback=result_state.get("feedback"),
        next_step_recommendation=result_state.get("next_step_recommendation"),
        misconceptions=result_state.get("misconceptions", []),
        personalized_learning_resources=result_state.get(
            "personalized_learning_resources", []
        ),
        student_recommendations=result_state.get("student_recommendations", []),
        educator_recommendations=result_state.get("educator_recommendations", []),
        performance_summary=result_state.get("performance_summary"),
    )
