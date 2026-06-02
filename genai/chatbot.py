from groq import Groq
from sqlalchemy import text
from db.database import get_session
from utils.logger import log
from utils.config_loader import get_env, load_config

config = load_config()
client = Groq(api_key=get_env("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"

DB_SCHEMA = """
PostgreSQL Database Schema:

TABLE: violations
  - id (int)
  - worker_id (text) e.g. 'W-01', 'W-02'
  - violation_type (text) e.g. 'NO-Hardhat', 'Fall-Detected', 'NO-Safety Vest'
  - severity (text) 'CRITICAL' or 'HIGH'
  - zone (text) e.g. 'general'
  - confidence (float) 0.0 to 1.0
  - timestamp (timestamp)
  - snapshot_path (text)

TABLE: alerts
  - id (int)
  - worker_id (text)
  - message (text)
  - severity (text) 'CRITICAL' or 'HIGH'
  - violation_type (text)
  - timestamp (timestamp)
  - resolved (boolean)

TABLE: workers
  - id (int)
  - worker_id (text)
  - first_seen (timestamp)
  - last_seen (timestamp)
"""

SQL_EXAMPLES = """
Examples of question → SQL:

Q: How many violations today?
SQL: SELECT COUNT(*) as total FROM violations WHERE DATE(timestamp) = CURRENT_DATE

Q: Which worker had most violations?
SQL: SELECT worker_id, COUNT(*) as count FROM violations GROUP BY worker_id ORDER BY count DESC LIMIT 1

Q: Any falls detected?
SQL: SELECT worker_id, timestamp FROM violations WHERE violation_type = 'Fall-Detected' ORDER BY timestamp DESC LIMIT 10

Q: Most common violations?
SQL: SELECT violation_type, COUNT(*) as count FROM violations GROUP BY violation_type ORDER BY count DESC LIMIT 5

Q: How many critical violations?
SQL: SELECT COUNT(*) as total FROM violations WHERE severity = 'CRITICAL'

Q: How many workers tracked?
SQL: SELECT COUNT(DISTINCT worker_id) as total FROM workers

Q: Violations in last hour?
SQL: SELECT worker_id, violation_type, severity, timestamp FROM violations WHERE timestamp >= NOW() - INTERVAL '1 hour' ORDER BY timestamp DESC

Q: Compliance rate?
SQL: SELECT COUNT(DISTINCT w.worker_id) as total_workers, COUNT(DISTINCT v.worker_id) as violating FROM workers w LEFT JOIN violations v ON w.worker_id = v.worker_id AND DATE(v.timestamp) = CURRENT_DATE

Q: Recent alerts?
SQL: SELECT worker_id, message, severity, timestamp FROM alerts ORDER BY timestamp DESC LIMIT 10

Q: NO-Hardhat violations?
SQL: SELECT worker_id, timestamp, confidence FROM violations WHERE violation_type = 'NO-Hardhat' ORDER BY timestamp DESC LIMIT 20

Q: Violations by severity?
SQL: SELECT severity, COUNT(*) as count FROM violations GROUP BY severity ORDER BY count DESC

Q: Active workers today?
SQL: SELECT COUNT(DISTINCT worker_id) as active FROM workers WHERE DATE(last_seen) = CURRENT_DATE
"""


def _generate_sql(question: str, chat_history: list) -> str:
    history_text = ""
    if chat_history:
        history_text = "\nPrevious conversation:\n"
        for msg in chat_history[-4:]:
            history_text += f"{msg['role'].upper()}: {msg['content']}\n"

    prompt = f"""You are a PostgreSQL expert for a workplace safety monitoring system.
Convert the user question into a valid SQL SELECT query.

{DB_SCHEMA}

{SQL_EXAMPLES}

Rules:
- Only SELECT statements — never INSERT, UPDATE, DELETE, DROP
- For "today" use: DATE(timestamp) = CURRENT_DATE
- For "this week" use: timestamp >= NOW() - INTERVAL '7 days'
- For "last hour" use: timestamp >= NOW() - INTERVAL '1 hour'
- Always LIMIT results to 50 unless asking for counts
- Return ONLY the raw SQL query
- No markdown, no backticks, no explanation, no comments
{history_text}
Question: {question}
SQL:"""

    response = client.chat.completions.create(
        model = MODEL,
        messages = [{"role": "user", "content": prompt}],
        max_tokens = 300,
        temperature = 0.1,
    )
    sql = response.choices[0].message.content.strip()

    # strip markdown if model adds it
    sql = sql.replace("```sql", "").replace("```", "").strip()
    log.debug(f"Generated SQL: {sql}")
    return sql


def _run_sql(sql: str) -> list:
    session = get_session()
    try:
        result = session.execute(text(sql))
        rows   = result.fetchall()
        cols   = list(result.keys())
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        log.error(f"SQL execution failed: {e} | SQL: {sql}")
        return []
    finally:
        session.close()


def _summarize(question: str, results: list) -> str:
    if not results:
        return (
            "No data found for that query. The database may not have records "
            "matching your question yet — try running the live feed first to generate data."
        )

    prompt = f"""You are SafeBot, a workplace safety assistant.
A supervisor asked: "{question}"

Data from the safety database:
{results}

Instructions:
- Summarize clearly in 2-4 sentences
- Be specific — mention exact numbers, worker IDs, violation types, timestamps
- If it's a count query, lead with the number
- If no meaningful data, say so honestly
- Do NOT mention SQL, databases, or technical terms
- Tone: professional, direct, helpful"""

    response = client.chat.completions.create(
        model = MODEL,
        messages = [{"role": "user", "content": prompt}],
        max_tokens = 250,
    )
    return response.choices[0].message.content.strip()


def _is_safety_question(question: str) -> bool:
    """Check if question needs DB query or can be answered directly."""
    db_keywords = [
        "how many", "which worker", "violations", "falls", "detected",
        "compliance", "today", "week", "hour", "recent", "alert",
        "critical", "high", "worker", "most", "least", "trend",
        "show", "list", "count", "total", "any"
    ]
    q = question.lower()
    return any(kw in q for kw in db_keywords)


def ask(question: str, chat_history: list = []) -> str:
    try:
        if not _is_safety_question(question):
            # general safety question — answer directly without DB
            prompt = f"""You are SafeBot, a workplace safety assistant for a construction site.
Answer this question helpfully and concisely: {question}
Keep response under 3 sentences. Be practical and specific to construction safety."""
            response = client.chat.completions.create(
                model = MODEL,
                messages = [{"role": "user", "content": prompt}],
                max_tokens = 200,
            )
            return response.choices[0].message.content.strip()

        sql = _generate_sql(question, chat_history)
        results = _run_sql(sql)
        answer = _summarize(question, results)
        log.info(f"Chatbot Q: '{question}' | Rows: {len(results)}")
        return answer

    except Exception as e:
        log.error(f"Chatbot error: {e}")
        return "I encountered an error processing your question. Please try rephrasing it."


if __name__ == "__main__":
    from db.database import init_db
    init_db()

    questions = [
        "How many violations happened today?",
        "Which worker had the most violations?",
        "Were there any falls detected?",
        "What is the most common violation type?",
        "How many workers were tracked today?",
        "Show me violations in the last hour",
    ]

    history = []
    for q in questions:
        print(f"\nQ: {q}")
        a = ask(q, history)
        print(f"A: {a}")
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": a})