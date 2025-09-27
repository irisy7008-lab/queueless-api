from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
from rapidfuzz import process, fuzz
from openai import OpenAI
import json, os

app = FastAPI(title="QueueLess API", version="0.3.0")

# ---------- load seed data ----------
BASE_DIR = Path(__file__).resolve().parent
SEED_PATH = BASE_DIR / "data" / "roles_seed.json"

with open(SEED_PATH, "r", encoding="utf-8") as f:
    SEED: List[Dict[str, Any]] = json.load(f)

# ---------- request models ----------
#who is hiring for x role?
class SearchReq(BaseModel):
    role: str
    top_k: int = 3

# Tell me about x employer.
class EmployerReq(BaseModel):
    employerName: str

# Give me conversation starters.
class StartersReq(BaseModel):
    employerName: Optional[str] = None
    role: Optional[str] = None

# ---------- helpers ----------
def norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def get_employer(d: Dict[str, Any]) -> Dict[str, Any]:
    return d.get("employer", {}) or {}

def get_role(d: Dict[str, Any]) -> Dict[str, Any]:
    return d.get("role", {}) or {}

def get_skills(d: Dict[str, Any]) -> List[str]:
    v = d.get("skills", [])
    return v if isinstance(v, list) else []

def s(v: Any) -> str:
    return v if isinstance(v, str) else ""

def select_contacts(hiring_leads: Any) -> List[Dict[str, Any]]:
    """Rank, respect consent, return ≤2 contacts."""
    leads = hiring_leads if isinstance(hiring_leads, list) else []

    def score(c):
        sc = 0
        if c.get("is_hiring_manager"): sc += 3
        if c.get("is_on_site"): sc += 2
        if c.get("timeslot"): sc += 1
        return sc

    ranked = sorted(leads, key=score, reverse=True)[:2]
    out = []
    for c in ranked:
        consent = bool(c.get("opt_in"))
        out.append({
            "title": s(c.get("title")),
            "name": s(c.get("name")) if consent else None,
            "linkedin": s(c.get("linkedin_url")) if (consent and c.get("linkedin_url")) else None,
            "timeslot": s(c.get("timeslot")) if c.get("timeslot") else None
        })
    return out

def starters_local(employer: str, role: str) -> List[str]:
    base = role or "this role"
    return [
        f"What skills matter most for success in {base} at {employer}?",
        "Which teams would I collaborate with most as an intern?",
        "How do you support learning and feedback in the first 8–12 weeks?"
    ]

def call_openai(prompt: str) -> List[str]:
    """
    Call OpenAI using the new 1.x SDK. Tries a small list of models.
    Requires env var OPENAI_API_KEY.
    """
    if not os.getenv("OPENAI_API_KEY"):
        print("[Starters] No OPENAI_API_KEY in env → using local fallback")
        return []

    client = OpenAI()  # reads key from env automatically
    candidate_models = ["gpt-4o-mini", "gpt-4o"]  # try mini first, then 4o

    last_err = None
    for m in candidate_models:
        try:
            print(f"[Starters] Calling OpenAI with model: {m}")
            resp = client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            text = resp.choices[0].message.content.strip()
            # split into bullet-ish lines
            lines = [ln.strip("-• ").strip() for ln in text.split("\n") if ln.strip()]
            return lines[:3] if lines else []
        except Exception as e:
            print(f"[Starters] OpenAI error with {m}: {e}")
            last_err = e
            continue
    # if all models failed, return empty (caller will fallback to local)
    return []

# ---------- endpoints ----------
@app.get("/")
def root():
    return {"message": "QueueLess API. See /docs for Swagger UI."}

@app.get("/health")
def health():
    return {"ok": True, "records": len(SEED), "has_openai_key": bool(os.getenv("OPENAI_API_KEY"))}

@app.get("/roles")
def roles_list():
    """Debug helper: list role titles found in the seed."""
    return [s(get_role(r).get("title")) for r in SEED]

@app.post("/search")
def search(req: SearchReq):
    """
    Who’s hiring <role>?
    Fuzzy match against role.title + role.function (if present) + skills[].
    """
    # Active filter if present, default True
    pool = []
    for r in SEED:
        role = get_role(r)
        is_active = r.get("is_active", role.get("is_active", True))
        if is_active:
            pool.append(r)

    # Build searchable strings
    texts = []
    for idx, r in enumerate(pool):
        role = get_role(r)
        tokens = [
            s(role.get("title")),
            s(role.get("function")),          # may be missing
            " ".join([s(x) for x in get_skills(r)])
        ]
        searchable = " ".join([t for t in tokens if t])
        texts.append((idx, searchable))

    choices = [t[1] for t in texts]
    matches = process.extract(req.role, choices, scorer=fuzz.WRatio, limit=max(1, req.top_k))

    results = []
    for (_txt, _score, idx) in matches:
        record = pool[texts[idx][0]]
        emp, role = get_employer(record), get_role(record)
        results.append({
            "employerName": s(emp.get("name")),
            "roleTitle": s(role.get("title")),
            "boothCode": s(emp.get("boothCode")),
            "contacts": select_contacts(record.get("hiringLeads")),
            "links": record.get("links", []),
        })
    return {"results": results}

@app.post("/employer")
def employer(req: EmployerReq):
    """Tell me about <employer>: summary, links, booth."""
    name = norm(req.employerName)
    rows = [r for r in SEED if norm(get_employer(r).get("name")) == name]
    if not rows:
        return {"found": False}
    e = get_employer(rows[0])
    summary = e.get("summary") or f"{e.get('name')} is participating in the event."
    return {
        "found": True,
        "name": s(e.get("name")),
        "summary": s(summary),
        "website": s(e.get("website")),
        "linkedin": s(e.get("linkedin")),
        "boothCode": s(e.get("boothCode")),
    }

@app.post("/starters")
def starters(req: StartersReq):
    """
    Conversation starters for a company/role.
    Uses OpenAI if OPENAI_API_KEY is set; otherwise returns local suggestions.
    """
    employer = req.employerName or "this employer"
    role = req.role or "this role"
    prompt = (
        f"Given employer '{employer}' and role '{role}', write 3 short, specific conversation starters "
        "for a student at a career fair. Use only the given info; avoid inventing facts. "
        "Keep each under 18 words."
    )

    lines = call_openai(prompt)
    if lines:
        return {"starters": lines}
    # fallback
    return {"starters": starters_local(employer, role)}
