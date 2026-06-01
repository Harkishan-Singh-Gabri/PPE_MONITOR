from groq import Groq
from sqlalchemy import text
from db.database import get_session
from utils.logger import log
from utils.config_loader import get_env, load_config

config = load_config()
client = Groq(api_key=get_env("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"

DB_SCHEMA = """
Tables in the database:

1. violations
   - id, worker_id (e.g. 'W-01'), violation_type (e.g. 'NO-Hardhat', 'Fall-Detected'),
     severity ('CRITICAL','HIGH'), zone, confidence, timestamp, snapshot_path

2. alerts
   - id, worker_id, message, severity, violation_type, timestamp, resolved (bool)

3. workers
   - id, worker_id, first_seen, last_seen
"""


def _generate_sql(question: str, chat_history: list) -> str:
    history_text = ""
    if chat_history:
        history_text = "\nPrevious conversation:\n"
        for msg in chat_history[-4:]:
            history_text += f"{msg['role'].upper()}: {msg['content']}\n"

    prompt = f"""You are a SQL expert for a workplace safety monitoring system.
Convert the user's question into a valid PostgreSQL query.

{DB_SCHEMA}

Rules:
- Only SELECT statements
- For "today" use: DATE(timestamp) = CURRENT_DATE
- For worker counts use COUNT(DISTINCT worker_id)
- Always LIMIT to 50 rows max
- Return ONLY the SQL query, nothing else
- No markdown, no backticks, no explanation
{history_text}
Question: {question}
SQL:"""

    response = client.chat.completions.create(
        model      = MODEL,
        messages   = [{"role": "user", "content": prompt}],
        max_tokens = 200,
    )
    sql = response.choices[0].message.content.strip()
    log.debug(f"Generated SQL: {sql}")
    return sql


def _run_sql(sql: str) -> list:
    session = get_session()
    try:
        result = session.execute(text(sql))
        rows   = result.fetchall()
        cols   = result.keys()
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        log.error(f"SQL execution failed: {e}")
        return []
    finally:
        session.close()


def _summarize(question: str, results: list) -> str:
    if not results:
        return "No data found for that query."

    prompt = f"""You are a workplace safety assistant.
The supervisor asked: "{question}"

Query results:
{results}

Summarize in 2-3 clear, concise sentences.
Be direct and factual. Mention worker IDs, counts, timestamps where relevant.
Do not mention SQL or databases."""

    response = client.chat.completions.create(
        model      = MODEL,
        messages   = [{"role": "user", "content": prompt}],
        max_tokens = 200,
    )
    return response.choices[0].message.content.strip()


def ask(question: str, chat_history: list = []) -> str:
    try:
        sql     = _generate_sql(question, chat_history)
        results = _run_sql(sql)
        answer  = _summarize(question, results)
        log.info(f"Chatbot Q: {question} | Results: {len(results)} rows")
        return answer
    except Exception as e:
        log.error(f"Chatbot error: {e}")
        return "Sorry, I could not process that question. Please try rephrasing."


if __name__ == "__main__":
    from db.database import init_db
    init_db()

    history   = []
    questions = [
        "How many violations happened today?",
        "Which worker had the most violations?",
        "Were there any falls detected?",
    ]

    for q in questions:
        print(f"\nQ: {q}")
        answer = ask(q, history)
        print(f"A: {answer}")
        history.append({"role": "user",      "content": q})
        history.append({"role": "assistant", "content": answer})