# quiz.py
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, validator
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda

# ---------- Schema (matches your required format) ----------
class Option(BaseModel):
    id: str = Field(..., description="single lowercase letter id like 'a','b','c','d'")
    text: str

class Question(BaseModel):
    id: int
    question: str
    type: Literal["multiple-choice", "text-input"]
    options: Optional[List[Option]] = None
    correctAnswer: str
    acceptableAnswers: Optional[List[str]] = None

    @validator("options", always=True)
    def options_required_for_mc(cls, v, values):
        if values.get("type") == "multiple-choice":
            if not v or len(v) < 2:
                raise ValueError("multiple-choice requires >= 2 options")
        return v

    @validator("correctAnswer")
    def mc_correct_must_match_option_ids(cls, v, values):
        if values.get("type") == "multiple-choice":
            ids = {o.id for o in (values.get("options") or [])}
            if v not in ids:
                raise ValueError("correctAnswer must be one of the option ids")
        return v

class Quiz(BaseModel):
    title: str
    questions: List[Question]

# ---------- Formatting helper ----------
def _format_docs(docs):
    parts = []
    for d in docs:
        m = d.metadata
        src = m.get("source", "source")
        if "slide" in m:
            cite = f"[{src} slide {m['slide']}]"
        elif "heading" in m:
            cite = f"[{src} {m.get('heading','section')}]"
        else:
            cite = f"[{src}]"
        parts.append(f"{cite} {d.page_content.strip()}")
    return "\n---\n".join(parts)

# ---------- Chain builder ----------
def build_quiz_chain(retriever, llm, *, k: int = 12):
    parser = PydanticOutputParser(pydantic_object=Quiz)

    system = (
        "You are a strict quiz generator for a CS course. "
        "Use ONLY the provided context to write questions. "
        "If a fact isn't supported by the context, do not include it.\n"
        "Rules:\n"
        "- Output MUST strictly match the JSON schema below (no extra keys, no commentary).\n"
        "- For multiple-choice, provide 3–5 plausible options with single-letter ids ('a','b','c','d', ...), "
        "and ensure 'correctAnswer' matches one option's id.\n"
        "- For text-input, set 'acceptableAnswers' to common surface forms (lowercase strings).\n"
        "- Do NOT leak the context in the question text; write clean, independent questions.\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("system", "JSON schema:\n{schema}"),
        ("human",
         "Create a quiz titled: {title}\n"
         "Topic: {topic}\n"
         "Number of questions: {n}\n\n"
         "Use this context:\n{context}\n\n"
         "Return ONLY the JSON (no backticks)."),
    ])

    def prepare_inputs(inp: dict):
        topic = inp["topic"]
        n = int(inp["n"])
        title = inp["title"]
        # Call retriever with a STRING query
        docs = retriever.invoke(topic)
        context = _format_docs(docs)
        return {
            "context": context,
            "topic": topic,
            "n": n,
            "title": title,
            "schema": Quiz.schema_json(indent=2),
        }

    return RunnableLambda(prepare_inputs) | prompt | llm | parser

def make_quiz(retriever, llm, topic: str, n: int = 10, title: Optional[str] = None) -> Quiz:
    chain = build_quiz_chain(retriever, llm)
    title = title or f"{topic.title()} Quiz"
    return chain.invoke({"topic": topic, "n": n, "title": title})
