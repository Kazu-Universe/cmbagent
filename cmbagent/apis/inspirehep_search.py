"""
Live INSPIRE-HEP literature search for the inspirehep_context agent.

This is the module that cmbagent/agents/inspirehep_context/inspirehep_context.py's
docstring has referenced since the fork was created, but which was never
actually built - until now, inspirehep_context ran on pure LLM recall, which
is why every real run's literature verdicts carried a "recall-based, no live
retrieval tool available" caveat (correctly disclosed by the agent, but a
standing gap: a recall-based literature check can never support a
publishable claim).

Uses the public INSPIRE-HEP REST API:
    https://inspirehep.net/api/literature
Documented at https://github.com/inspirehep/rest-api-doc . No API key is
required; the API asks for polite usage (this module makes one request per
call, no crawling).

Design notes:
- Returns a formatted STRING, not structured data - the consumer is an LLM
  tool call, and a readable summary is what the agent needs to reason over.
- Errors return an explicit "INSPIRE TOOL ERROR" string rather than raising,
  so the agent visibly learns the live search failed and can disclose a
  recall-based fallback (per its yaml instructions) instead of the failure
  being swallowed and recall silently masquerading as a live result.
- Abstract snippets are truncated hard: the agent's instructions forbid
  reproducing abstracts at length; the snippet exists only to help the agent
  paraphrase accurately.
"""

import requests

INSPIRE_API_URL = "https://inspirehep.net/api/literature"

# Fields requested from the API - keep this tight; the full metadata records
# are large and mostly irrelevant for literature-verdict purposes.
_FIELDS = ",".join([
    "titles",
    "authors.full_name",
    "arxiv_eprints",
    "dois",
    "publication_info",
    "earliest_date",
    "citation_count",
    "abstracts",
])

_ABSTRACT_SNIPPET_CHARS = 300
_MAX_AUTHORS_SHOWN = 3
_REQUEST_TIMEOUT_S = 30


def search_inspire(query: str, max_results: int = 10, sort: str = "mostrecent") -> str:
    """
    Run one live INSPIRE-HEP literature search and return formatted results.

    Args:
        query: INSPIRE search query. Free text works; so does INSPIRE's
            structured syntax, e.g.:
              'entanglement entropy logarithmic correction black hole'
              't "entanglement entropy" and date > 2020'
              'a Solodukhin and t entanglement'
              'arxiv:1104.3712'
        max_results: number of records to return (1-25).
        sort: 'mostrecent' | 'mostcited' | 'bestmatch'.

    Returns:
        A formatted plain-text summary of the hits (title, authors, arXiv ID,
        DOI, journal, date, citation count, truncated abstract snippet), or a
        string beginning with "INSPIRE TOOL ERROR" if the live query could
        not be completed - in which case the caller must disclose that any
        literature statements are recall-based, not live-verified.
    """
    max_results = max(1, min(int(max_results), 25))
    if sort not in ("mostrecent", "mostcited", "bestmatch"):
        sort = "mostrecent"

    params = {
        "q": query,
        "size": max_results,
        "page": 1,
        "sort": sort,
        "fields": _FIELDS,
    }

    try:
        resp = requests.get(INSPIRE_API_URL, params=params, timeout=_REQUEST_TIMEOUT_S)
    except requests.RequestException as e:
        return (
            "INSPIRE TOOL ERROR: live query failed before receiving a response "
            f"({type(e).__name__}: {e}). Any literature statements you make now "
            "are recall-based, NOT live-verified - you must disclose this "
            "explicitly, per your instructions."
        )

    if resp.status_code != 200:
        return (
            f"INSPIRE TOOL ERROR: HTTP {resp.status_code} from the INSPIRE API "
            f"for query {query!r}. Any literature statements you make now are "
            "recall-based, NOT live-verified - you must disclose this "
            "explicitly, per your instructions."
        )

    try:
        payload = resp.json()
        hits = payload["hits"]["hits"]
        total = payload["hits"]["total"]
    except (ValueError, KeyError) as e:
        return (
            "INSPIRE TOOL ERROR: could not parse the INSPIRE API response "
            f"({type(e).__name__}: {e}). Any literature statements you make now "
            "are recall-based, NOT live-verified - you must disclose this "
            "explicitly, per your instructions."
        )

    if not hits:
        return (
            f"INSPIRE live search completed successfully: 0 results for query "
            f"{query!r} (sort={sort}). This is a genuine live-verified empty "
            "result, not a tool failure - if the question is whether such a "
            "paper exists, an empty result is evidence of absence in INSPIRE's "
            "index for this query (though query phrasing matters; consider "
            "1-2 rephrasings before concluding)."
        )

    lines = [
        f"INSPIRE live search results for query {query!r} "
        f"(sort={sort}; showing {len(hits)} of {total} total matches):",
        "",
    ]

    for i, hit in enumerate(hits, 1):
        md = hit.get("metadata", {})

        title = "(no title)"
        titles = md.get("titles") or []
        if titles:
            title = titles[0].get("title", "(no title)")

        authors = md.get("authors") or []
        author_names = [a.get("full_name", "?") for a in authors[:_MAX_AUTHORS_SHOWN]]
        author_str = "; ".join(author_names) if author_names else "(no authors listed)"
        if len(authors) > _MAX_AUTHORS_SHOWN:
            author_str += " et al."

        arxiv_ids = [e.get("value", "?") for e in (md.get("arxiv_eprints") or [])]
        arxiv_str = ", ".join(arxiv_ids) if arxiv_ids else "(no arXiv ID)"

        dois = [d.get("value", "?") for d in (md.get("dois") or [])]
        doi_str = dois[0] if dois else "(no DOI)"

        pub = "(unpublished / not listed)"
        pub_info = md.get("publication_info") or []
        if pub_info:
            j = pub_info[0]
            jtitle = j.get("journal_title", "")
            jvol = j.get("journal_volume", "")
            jyear = j.get("year", "")
            if jtitle:
                pub = f"{jtitle} {jvol} ({jyear})".strip()

        date = md.get("earliest_date", "(no date)")
        citations = md.get("citation_count", "n/a")

        abstract_snippet = ""
        abstracts = md.get("abstracts") or []
        if abstracts:
            raw = abstracts[0].get("value", "")
            if raw:
                snippet = raw[:_ABSTRACT_SNIPPET_CHARS]
                if len(raw) > _ABSTRACT_SNIPPET_CHARS:
                    snippet += "..."
                abstract_snippet = f"   abstract (truncated): {snippet}"

        lines.append(f"{i}. {title}")
        lines.append(f"   authors: {author_str}")
        lines.append(f"   arXiv: {arxiv_str} | DOI: {doi_str}")
        lines.append(f"   published: {pub} | earliest date: {date} | citations: {citations}")
        if abstract_snippet:
            lines.append(abstract_snippet)
        lines.append("")

    lines.append(
        "Reminder: paraphrase results in your own words with identifiers "
        "attached; do not reproduce abstracts. Report the exact query strings "
        "you used in your 'Sources Consulted' section so the search is "
        "auditable and reproducible."
    )

    return "\n".join(lines)
