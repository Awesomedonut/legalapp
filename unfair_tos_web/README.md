# unfair_tos Web Tool

Small web app that:
1. Takes a website URL.
2. Finds a likely Terms-of-Service page.
3. Extracts clauses.
4. Classifies clauses using LegalBench `unfair_tos` categories.
5. Returns an overall verdict: `Unfair` if any unfair category is detected, otherwise `Fair`.

## Run

```bash
cd /Users/donut/git/legalbench/unfair_tos_web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5050`

## Notes

- Categories come from `tasks/unfair_tos` in LegalBench:
  - Arbitration
  - Unilateral change
  - Content removal
  - Jurisdiction
  - Choice of law
  - Limitation of liability
  - Unilateral termination
  - Contract by using
  - Other
- This implementation uses deterministic keyword matching for transparency and speed.
- It is a screening tool, not legal advice.
