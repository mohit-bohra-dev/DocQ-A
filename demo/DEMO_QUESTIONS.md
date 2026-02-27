# Demo Question Cheat-Sheet

Sample questions to try during a recruiter demo. Upload a PDF first, then use
these questions to showcase the system's RAG capabilities across different
complexity levels.

---

## Tier 1 — Factual Retrieval (Shows: accuracy & source grounding)

> *These questions have clear, specific answers in the document.*

- "What is the main purpose of this document?"
- "Who are the authors or contributors listed?"
- "What is the document dated / when was it published?"
- "What are the key findings or conclusions?"
- "List the main sections or chapters covered."

**What to highlight:** Point out the **Source References** panel — the answer
cites the exact page number where the information was found.

---

## Tier 2 — Synthesis (Shows: multi-chunk reasoning)

> *These require combining information from multiple parts of the document.*

- "Summarise the three most important points from this document."
- "What problem does this document address, and what solution does it propose?"
- "Compare the advantages and disadvantages mentioned."
- "What evidence is provided to support the main argument?"
- "What are the limitations or caveats acknowledged?"

**What to highlight:** The **Confidence Score** — watch it be higher when the
answer is well-supported across multiple retrieved chunks.

---

## Tier 3 — Edge Cases (Shows: robustness & honest handling)

> *These test how the system handles ambiguity or out-of-scope questions.*

- Ask something **not in the document** (e.g., a completely unrelated topic)
  → The system should say it can't find the answer rather than hallucinating.
- Ask the same question twice with different phrasing
  → Results should be semantically consistent.
- Upload **two different documents**, then filter by one
  → Demonstrates per-document filtering capability.

**What to highlight:** The **Document Filter** dropdown — showing you can
isolate queries to a specific document by name.

---

## Demo Flow Tips

1. **Start with the health panel** (sidebar) — shows all components are live
2. **Upload a well-known doc** (e.g., a research paper or product spec)
3. **Ask a Tier 1 question** — quick win, recruiter sees a grounded answer
4. **Ask a Tier 2 question** — shows reasoning depth
5. **Show Conversation History** — demonstrates stateful multi-turn UX
6. **Mention the architecture**: FastAPI backend → embeddings → vector search
   → Gemini LLM → grounded answer with citations

---

## Suggested Sample Documents

| Document Type | Why It Works Well |
|---|---|
| Research paper (arXiv PDF) | Dense, factual — great for showing precision |
| Company annual report | Multi-section — great for synthesis questions |
| Technical specification | Structured — great for "what does X mean?" queries |
| Your own CV / portfolio PDF | Personal touch — recruiter can ask about your skills! |
