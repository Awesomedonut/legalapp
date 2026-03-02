from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import bs4
import requests
from flask import Flask, render_template, request


app = Flask(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36"
)

UNFAIR_CATEGORIES: Dict[str, List[str]] = {
    "Arbitration": [
        "arbitration",
        "binding arbitration",
        "waive your right to a trial",
        "class action waiver",
    ],
    "Unilateral change": [
        "reserve the right to modify",
        "may change these terms at any time",
        "without prior notice",
        "sole discretion",
    ],
    "Content removal": [
        "remove or edit",
        "remove content",
        "take down",
        "delete content",
    ],
    "Jurisdiction": [
        "exclusive jurisdiction",
        "venue",
        "courts located in",
        "submit to the jurisdiction",
    ],
    "Choice of law": [
        "governed by the laws of",
        "choice of law",
        "laws of the state of",
    ],
    "Limitation of liability": [
        "limitation of liability",
        "not liable",
        "shall not be liable",
        "consequential damages",
        "loss of profits",
    ],
    "Unilateral termination": [
        "suspend or terminate",
        "terminate your account",
        "at any time and for any reason",
        "without notice",
    ],
    "Contract by using": [
        "by using",
        "by accessing",
        "you agree to be bound",
        "your use of the service constitutes acceptance",
    ],
}

TOS_HINTS = [
    "terms",
    "terms-of-service",
    "terms-of-use",
    "tos",
    "legal",
    "conditions",
    "user-agreement",
]


@dataclass
class ClauseResult:
    text: str
    category: str


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def fetch_html(url: str) -> str:
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": USER_AGENT},
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def discover_tos_url(base_url: str) -> Tuple[str, Optional[str]]:
    try:
        html = fetch_html(base_url)
    except Exception as exc:
        return base_url, f"Could not fetch site: {exc}"

    soup = bs4.BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        text = tag.get_text(" ", strip=True).lower()
        full = urljoin(base_url, href)
        target = f"{href.lower()} {text}"
        if any(h in target for h in TOS_HINTS):
            return full, None

    # fallback guesses
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    for candidate in ["/terms", "/terms-of-service", "/tos", "/legal/terms"]:
        guess = urljoin(root, candidate)
        try:
            fetch_html(guess)
            return guess, None
        except Exception:
            continue

    return base_url, "No dedicated ToS link found; used the provided URL."


def extract_text_from_html(html: str) -> str:
    soup = bs4.BeautifulSoup(html, "html.parser")

    for bad in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        bad.decompose()

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def split_clauses(text: str) -> List[str]:
    raw = re.split(r"(?<=[.;])\s+", text)
    clauses = []
    for c in raw:
        c = c.strip()
        if len(c) < 40:
            continue
        if len(c) > 1200:
            c = c[:1200]
        clauses.append(c)
    return clauses


def classify_clause(clause: str) -> str:
    lowered = clause.lower()
    for category, patterns in UNFAIR_CATEGORIES.items():
        if any(p in lowered for p in patterns):
            return category
    return "Other"


def analyze_tos(text: str) -> Dict[str, object]:
    clauses = split_clauses(text)
    classified: List[ClauseResult] = []
    for clause in clauses:
        label = classify_clause(clause)
        if label != "Other":
            classified.append(ClauseResult(text=clause, category=label))

    unfair_count = len(classified)
    verdict = "Unfair" if unfair_count > 0 else "Fair"

    by_category: Dict[str, int] = {}
    for item in classified:
        by_category[item.category] = by_category.get(item.category, 0) + 1

    return {
        "verdict": verdict,
        "unfair_count": unfair_count,
        "total_clauses": len(clauses),
        "category_counts": dict(sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)),
        "flagged": classified[:30],
    }


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    source_url = None
    note = None
    if request.method == "POST":
        user_url = normalize_url(request.form.get("url", ""))
        if not user_url:
            error = "Please enter a valid website URL."
        else:
            source_url, note = discover_tos_url(user_url)
            try:
                html = fetch_html(source_url)
                text = extract_text_from_html(html)
                result = analyze_tos(text)
            except Exception as exc:
                error = f"Failed to analyze ToS: {exc}"

    return render_template("index.html", result=result, error=error, source_url=source_url, note=note)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
