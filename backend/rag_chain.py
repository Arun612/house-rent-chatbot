# rag_chain.py
"""
LangChain LCEL RAG chain with conversation-aware retrieval.
Uses pure langchain_core primitives to avoid missing module issues.
"""
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from config import GROQ_API_KEY, GROQ_LLM_MODEL, TOP_K
from vector_store import get_retriever

# ── LLM ───────────────────────────────────────────────────────────────────────
llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_LLM_MODEL,
    temperature=0.1,
    max_tokens=1024,
)

# ── Prompt: Condense follow-up question into standalone question ───────────────
_CONDENSE_PROMPT = ChatPromptTemplate.from_messages([
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
    (
        "human",
        "Given the conversation history above, rephrase my latest message into a "
        "clear, self-contained question that can be understood without any prior context. "
        "Output only the rephrased question — no explanation.",
    ),
])

# ── Prompt: Answer using retrieved context ────────────────────────────────────
_ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are RentChat, a highly professional and intelligent AI assistant specialized in analyzing housing and rental agreements.
Your absolute strict rule is to provide answers based ONLY on the provided document context.

Follow these strict guidelines:
1. **Be Direct & Natural**: Start with a direct answer. Do NOT use robotic intro phrases like "According to the provided document".
2. **Beautiful Formatting**: Use Markdown extensively. Use bold text for key terms, amounts, dates, or emphasis.
3. **Thorough yet Concise**: Give a complete answer based on the context, but avoid fluff.
4. **STRICTLY NO HALLUCINATIONS OR OUTSIDE KNOWLEDGE**: If the answer is not explicitly contained in the provided Document Context, or if the user asks a general knowledge question (e.g. about celebrities, coding, sports, history), you MUST reject it by stating: "I'm sorry, but I can only answer questions related to the provided rental agreement document." Do NOT use your pre-trained knowledge to answer.
5. **Cite Pages**: If a specific page number is highly relevant, mention it naturally in parentheses.

Document Context:
{context}""",
    ),
    MessagesPlaceholder("chat_history"),
    ("human", "Question: {input}\n\nReminder: If the answer is not in the document context above, say 'I'm sorry, but I can only answer questions related to the provided rental agreement document.' Do NOT use outside knowledge."),
])


# ── History helper ─────────────────────────────────────────────────────────────
def _to_lc_messages(messages: list[dict]) -> list:
    """Convert stored {role, content} dicts → LangChain message objects."""
    lc_msgs = []
    for msg in messages:
        if msg["role"] == "human":
            lc_msgs.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            lc_msgs.append(AIMessage(content=msg["content"]))
    return lc_msgs


def _format_docs(docs: list) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


# ── Main entry ────────────────────────────────────────────────────────────────
def ask(question: str, doc_id: str, history_messages: list[dict]) -> dict:
    """Run the pure LCEL RAG chain."""
    retriever = get_retriever(doc_id, top_k=TOP_K)
    chat_history = _to_lc_messages(history_messages)

    # 1. Condense follow-up question if there is history
    if chat_history:
        condense_chain = _CONDENSE_PROMPT | llm | StrOutputParser()
        standalone_question = condense_chain.invoke({
            "input": question,
            "chat_history": chat_history
        })
    else:
        standalone_question = question

    # 2. Retrieve documents using the standalone question
    docs = retriever.invoke(standalone_question)

    # 3. Generate the answer grounded in the retrieved docs
    answer_chain = _ANSWER_PROMPT | llm | StrOutputParser()
    answer = answer_chain.invoke({
        "context": _format_docs(docs),
        "chat_history": chat_history,
        "input": question,
    })

    # 4. De-duplicate sources
    sources = []
    seen: set[str] = set()
    for doc in docs:
        page = doc.metadata.get("page", "?")
        snippet = doc.page_content[:250].strip()
        key = f"{page}:{snippet[:50]}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "page": page,
                "snippet": snippet,
                "source": doc.metadata.get("source", ""),
            })

    return {"answer": answer, "sources": sources}


async def ask_stream(question: str, doc_id: str, history_messages: list[dict]):
    """Run the pure LCEL RAG chain with streaming."""
    retriever = get_retriever(doc_id, top_k=TOP_K)
    chat_history = _to_lc_messages(history_messages)

    if chat_history:
        condense_chain = _CONDENSE_PROMPT | llm | StrOutputParser()
        standalone_question = await condense_chain.ainvoke({
            "input": question,
            "chat_history": chat_history
        })
    else:
        standalone_question = question

    docs = await retriever.ainvoke(standalone_question)

    answer_chain = _ANSWER_PROMPT | llm | StrOutputParser()

    sources = []
    seen: set[str] = set()
    for doc in docs:
        page = doc.metadata.get("page", "?")
        snippet = doc.page_content[:250].strip()
        key = f"{page}:{snippet[:50]}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "page": page,
                "snippet": snippet,
                "source": doc.metadata.get("source", ""),
            })

    full_answer = ""
    async for chunk in answer_chain.astream({
        "context": _format_docs(docs),
        "chat_history": chat_history,
        "input": question,
    }):
        full_answer += chunk
        yield {"chunk": chunk}

    yield {"sources": sources, "full_answer": full_answer}
