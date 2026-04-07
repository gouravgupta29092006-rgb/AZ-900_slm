"""
Answer Generator Module
-----------------------
Generates structured answers from retrieved chunks using Ollama
with the Mistral model. Fully offline — no external API calls.

Supports two modes:
  1. Topic queries  → definition + explanation + example + MCQ
  2. Exam questions → identifies correct answer + detailed explanation
"""

import re
import json
import random
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"


def get_generator():
    """Verify Ollama is running and model is available."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        print(f"  🧠 Ollama models available: {models}")
        if not any(MODEL_NAME in m for m in models):
            print(f"  ⚠️  Model '{MODEL_NAME}' not found. Pull it with: ollama pull {MODEL_NAME}")
        else:
            print(f"  ✅ Generation model ready: {MODEL_NAME}")
    except Exception as e:
        print(f"  ❌ Cannot connect to Ollama: {e}")
        print("  💡 Make sure Ollama is running: ollama serve")


def _generate(prompt: str, max_tokens: int = 512, json_mode: bool = False) -> str:
    """Generate text using Ollama's Mistral model."""
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.3,
            "top_p": 0.9,
        },
    }
    if json_mode:
        payload["format"] = "json"
        
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama. Is it running? Start with: ollama serve")
        return "Error: Ollama not running."
    except Exception as e:
        print(f"❌ Generation error: {e}")
        return "Error generating response."


# ── Exam question detection ────────────────────────────────────────────

def _is_exam_question(query: str) -> bool:
    """Detect if the query is a pasted exam-style MCQ question."""
    query_lower = query.lower()
    option_pattern = re.findall(r'[•\-]?\s*[A-Ea-e][.)]\s', query)
    has_options = len(option_pattern) >= 3

    has_exam_keywords = any(kw in query_lower for kw in [
        "which of the following",
        "which two",
        "which three",
        "select the correct",
        "what should you",
        "you need to",
        "you plan to",
        "should you include",
        "should you recommend",
        "what is the best",
        "choose the best",
    ])

    return has_options or has_exam_keywords


def _answer_exam_question(query: str, context: str) -> dict:
    """Answer an exam-style MCQ with detailed explanation."""
    prompt = (
        f"You are an expert Microsoft Azure instructor helping a student "
        f"prepare for the AZ-900 certification exam.\n\n"
        f"## Exam Question:\n{query}\n\n"
        f"## Reference Material:\n{context}\n\n"
        f"## Instructions:\n"
        f"1. Identify the correct answer(s) from the options given.\n"
        f"2. State the correct answer clearly.\n"
        f"3. Explain in detail WHY each correct option is right.\n"
        f"4. Explain WHY each wrong option is incorrect.\n"
        f"5. Provide any additional context that would help understand the concept.\n\n"
        f"## Your Answer:"
    )
    full_response = _generate(prompt, max_tokens=800)

    return {
        "mode": "exam_question",
        "answer": full_response,
    }


# ── Topic-mode generators ──────────────────────────────────────────────

def generate_definition(query: str, context: str) -> str:
    """Generate a full, detailed definition."""
    prompt = (
        f"You are an expert Microsoft Azure instructor helping a student "
        f"prepare for the AZ-900 certification exam.\n\n"
        f"Using the reference material below, provide a complete and detailed "
        f"definition of '{query}'. Include what it is, what it does, why it "
        f"matters in cloud computing, and any key characteristics.\n\n"
        f"Reference Material:\n{context}\n\n"
        f"Provide a thorough definition (4-5 sentences):"
    )
    return _generate(prompt, max_tokens=400)


def generate_explanation(query: str, context: str) -> str:
    """Generate a thorough, easy-to-understand explanation."""
    prompt = (
        f"You are an expert Microsoft Azure instructor.\n\n"
        f"Explain '{query}' in detail so that a beginner can fully understand it. "
        f"Cover how it works, its key features, benefits, and when you would use it. "
        f"Use simple language but be thorough.\n\n"
        f"Reference Material:\n{context}\n\n"
        f"Provide a detailed explanation (5-6 sentences):"
    )
    return _generate(prompt, max_tokens=500)


def generate_example(query: str, context: str) -> str:
    """Generate a detailed real-world example."""
    prompt = (
        f"You are an expert Microsoft Azure instructor.\n\n"
        f"Give a detailed, realistic real-world example of how '{query}' is used "
        f"in practice. Describe a specific business scenario step by step, "
        f"explaining what happens and why this matters.\n\n"
        f"Reference Material:\n{context}\n\n"
        f"Provide a detailed real-world example (4-5 sentences):"
    )
    return _generate(prompt, max_tokens=400)


def generate_mcq(query: str, context: str) -> dict:
    """Generate a multiple-choice question with 4 options."""
    prompt = (
        f"Create one AZ-900 exam-style multiple-choice question about '{query}'.\n\n"
        f"Reference Material:\n{context}\n\n"
        f"Format your response EXACTLY like this (no extra text):\n"
        f"Question: [your question here]\n"
        f"A. [option A]\n"
        f"B. [option B]\n"
        f"C. [option C]\n"
        f"D. [option D]\n"
        f"Correct: [letter]\n"
        f"Explanation: [why this is correct]"
    )
    raw = _generate(prompt, max_tokens=300)
    return _parse_mcq(raw, query, context)


def _parse_mcq(raw: str, query: str, context: str) -> dict:
    """Parse MCQ output into structured format."""
    lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]

    question = ""
    options = []
    correct_answer = ""
    explanation = ""

    for line in lines:
        if line.lower().startswith("question:"):
            question = line.split(":", 1)[1].strip()
        elif re.match(r'^[A-Da-d][.)]\s', line):
            letter = line[0].upper()
            text = line[2:].strip().lstrip(". )")
            options.append({"label": letter, "text": text})
        elif line.lower().startswith("correct:"):
            ans = line.split(":", 1)[1].strip()
            if ans and ans[0].upper() in "ABCD":
                correct_answer = ans[0].upper()
        elif line.lower().startswith("explanation:"):
            explanation = line.split(":", 1)[1].strip()

    if len(options) < 4 or not question:
        return _fallback_mcq(query, context)

    if not correct_answer and options:
        correct_answer = options[0]["label"]

    result = {
        "question": question,
        "options": options,
        "correct_answer": correct_answer,
    }
    if explanation:
        result["explanation"] = explanation

    return result


def _fallback_mcq(query: str, context: str) -> dict:
    """Create a template-based MCQ as fallback."""
    correct_text = f"A cloud service related to {query}"
    distractors = [
        "A physical hardware component only",
        "A service unrelated to Azure",
        "An on-premises-only solution",
    ]
    random.shuffle(distractors)

    options = [
        {"label": "A", "text": correct_text},
        {"label": "B", "text": distractors[0]},
        {"label": "C", "text": distractors[1]},
        {"label": "D", "text": distractors[2]},
    ]

    random.shuffle(options)
    for i, opt in enumerate(options):
        opt["label"] = chr(65 + i)

    correct_label = next(
        opt["label"] for opt in options if opt["text"] == correct_text
    )

    return {
        "question": f"Which of the following best describes '{query}' in the context of Azure?",
        "options": options,
        "correct_answer": correct_label,
    }


# ── Main entry point ───────────────────────────────────────────────────

def generate_answer(query: str, retrieved_chunks: list[dict], history_context: list[dict] = None) -> dict:
    """
    Generate a full structured answer from retrieved chunks.

    Auto-detects whether the query is:
      - An exam question → returns correct answer + explanation
      - A topic query   → returns definition + explanation + example + MCQ
    """
    context_parts = [r["chunk"] for r in retrieved_chunks]
    context = "\n\n---\n\n".join(context_parts)

    # Truncate context to stay within model limits
    context_words = context.split()
    if len(context_words) > 800:
        context = " ".join(context_words[:800])

    if history_context:
        hist_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history_context[-4:]]) # Keep last 4 turns
        context = f"### Previous Conversation History for Context:\n{hist_str}\n\n### Retrieved Reference Document:\n{context}"

    sources = [
        {"chunk_index": r["index"], "relevance_score": round(r["score"], 4)}
        for r in retrieved_chunks
    ]

    # ── Exam question mode ──────────────────────────────────────────
    if _is_exam_question(query):
        exam_result = _answer_exam_question(query, context)
        return {
            "query": query,
            **exam_result,
            "sources": sources,
        }

    # ── Topic learning mode ─────────────────────────────────────────

    prompt = (
        f"You are an expert Microsoft Azure instructor helping a student.\n\n"
        f"Topic: '{query}'\n\n"
        f"Reference Material:\n{context}\n\n"
        f"Instructions: Based on the reference material, perfectly format your response as a JSON object with the following keys:\n"
        f"- \"definition\": A clear definition (2-3 sentences)\n"
        f"- \"simple_explanation\": A beginner-friendly explanation (3-4 sentences)\n"
        f"- \"real_world_example\": A detailed business scenario example (3-4 sentences)\n"
        f"- \"mcq\": A nested object with \"question\", \"options\" (a list of 4 objects with \"label\" like 'A' and \"text\"), and \"correct_answer\" (the letter, e.g., 'A'), and \"explanation\" (why it's correct).\n\n"
        f"Return ONLY valid JSON."
    )

    try:
        raw_json_str = _generate(prompt, max_tokens=1500, json_mode=True)
        
        # Strip potential markdown formatting like ```json ... ```
        if "```json" in raw_json_str:
            raw_json_str = raw_json_str.split("```json")[-1].split("```")[0].strip()
        elif "```" in raw_json_str:
            raw_json_str = raw_json_str.split("```")[-1].split("```")[0].strip()
            
        result = json.loads(raw_json_str)
        
        definition = result.get("definition", "N/A")
        explanation = result.get("simple_explanation", "N/A")
        example = result.get("real_world_example", "N/A")
        mcq = result.get("mcq", _fallback_mcq(query, context))
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        definition = "Error generating content."
        explanation = "Error generating content."
        example = "Error generating content."
        mcq = _fallback_mcq(query, context)

    return {
        "query": query,
        "mode": "topic_learning",
        "definition": definition,
        "simple_explanation": explanation,
        "real_world_example": example,
        "mcq": mcq,
        "sources": sources,
    }
