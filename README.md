# S&P Compliance Analyzer

An AI tool that reviews screenplay/script content against broadcast
Standards & Practices (S&P) guidelines and actively flags violations —
built for a streaming platform's compliance review workflow, where a human
reviewer would otherwise read every script line by line looking for
content that needs a cut, a warning, or a rewrite before air.

## How it works

1. **Input**: paste script text, or upload a document (scanned pages go
   through Mistral OCR first).
2. **Language detection**: identifies the primary language, with explicit
   handling for South Asian scripts (Bengali, Hindi, Tamil, Telugu,
   Gujarati, Marathi, Punjabi, Urdu, Malayalam, Kannada, Odia, Assamese) —
   Bengali script detection in particular is a first-class case, not an
   afterthought.
3. **Violation detection**: an OpenAI-backed reviewer, prompted to be
   deliberately aggressive ("err on the side of flagging rather than
   missing violations"), scans the content and returns structured
   violations with an explanation per flag.
4. **Suggested fixes**: for each violation, generates a compliant revision
   — the minimum edit needed to resolve it — in the same language as the
   original content, not just in English.
5. **Export**: results and suggested edits export to Word/Excel/PDF for
   handoff to the compliance team.

`app.py` is the current version. `snp6.py` is an earlier, simpler
standalone iteration of the same idea, kept for reference.

## Stack

Streamlit, OpenAI API, Mistral OCR API, `python-docx` / `openpyxl` /
`reportlab` (exports), Plotly (results visualization).

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Needs `OPENAI_API_KEY` and `MISTRAL_API_KEY` via Streamlit secrets
(`.streamlit/secrets.toml`) — read through `st.secrets`, never hardcoded.
The app includes a lightweight login gate (email-domain check); it's
demo-grade access control, not production auth.
