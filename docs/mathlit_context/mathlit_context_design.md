# mathlit_context: design for review

A mathematics literature agent for the hep-th extension of CMBAgent.
Status: design agreed with Kazu (5 October 2026); no code written yet.

## 1. Why

`inspirehep_context` searches INSPIRE, which indexes physics well and
mathematics only partially. The fuzzy del Pezzo novelty scan (1 October 2026)
could not see Ishii–Ueda (arXiv:0911.4529) at all, and the key prior art for
one of its claims (perfect matchings and exceptional collections; moduli of
Bondal quivers) is in the mathematics literature. Work at the physics–maths
boundary needs a search that sees both sides.

## 2. Scope and boundary

- **mathlit_context**: mathematics papers (arXiv math.* and journals indexed by
  zbMATH Open). Classifies results as proved / special cases / conjectured /
  folklore / disputed.
- **inspirehep_context**: unchanged; physics literature.
- **Separate agents, separate plan steps.** Narrow scopes and separate contexts
  avoid shared blind spots, and keep each literature step bounded (the
  known cost driver).
- **The key new behaviour is translation**: physics phrasing is mapped to
  mathematical terminology before searching, and the map is reported.

## 3. Tools

Both follow `apis/inspirehep_search.py`: one request per call, a formatted
string as the return value, short abstract snippets, and an explicit
`"... TOOL ERROR ..."` string instead of raising.

| Tool | Backend | Signature (proposed) | Returns |
|---|---|---|---|
| `search_zbmath` | zbMATH Open REST API (api.zbmath.org) | `search_zbmath(query: str, max_results: int = 10) -> str` | Title, authors, year, source, zbMATH ID, DOI / arXiv ID, MSC codes; reviewer summary only where the API licenses it |
| `search_arxiv_math` | arXiv API (export.arxiv.org) | `search_arxiv_math(query: str, categories: str = "math.AG,math.RT,math.SG,math.DG,math.QA,math-ph", max_results: int = 10) -> str` | Title, authors, date, arXiv ID, primary category, abstract snippet |

To verify before coding (Claude Code should read the live API docs):

- the exact zbMATH Open search endpoint, query syntax and which fields come
  back without a licence (abstracts and reviews are often excluded);
- polite-use limits for both APIs (the arXiv API asks for a pause between
  calls);

Deferred: a cross-field citation graph (OpenAlex or similar) to replace the
`refersto` queries that failed in the scan. Add it as a third tool only after
checking its current API.

## 4. Prompt

Draft in `mathlit_context.yaml`, in the same format as
`inspirehep_context.yaml`. Differences:

- a required **terminology map** (physics → mathematics) before searching;
- searches across **both** tools, 3–6 phrasings, author- and MSC-based
  queries where helpful;
- a **status** classification suited to mathematics (proved / special cases /
  conjectured / folklore / disputed), noting that physics derivations are not
  proofs;
- **Gaps** must name indexes not covered (e.g. MathSciNet-only records).

## 5. Integration checklist

Every item maps to a known bug class in CLAUDE.md.

- [ ] `cmbagent/agents/mathlit_context/` with `mathlit_context.py` (copy of
      the `inspirehep_context` class) and `mathlit_context.yaml`
- [ ] `cmbagent/apis/zbmath_search.py`, `cmbagent/apis/arxiv_math_search.py`
- [ ] Tool registration in `cmbagent/functions/registration.py`, for
      `mathlit_context` only
- [ ] Agent-name allowlists (bug class 7): `planner_response_formatter`
      `Literal`, `status.py` (five places), `planning.py` `needed_agents`
- [ ] Model routing in `utils.py` (`default_agents_llm_model`, price table) and a
      `mathlit_context_model` parameter in `deep_research`: Sonnet 5.5
- [ ] `ToolSafeMessageHistoryLimiter` window (bug class 10): 70, as for
      `inspirehep_context`
- [ ] `human_input_mode="NEVER"` (bug class 14)
- [ ] Step-summary extraction finds it without a formatter (bug class 9)
- [ ] Planner instructions: when to assign `mathlit_context`, versus
      `inspirehep_context`
- [ ] Register `search_zbmath` and `search_arxiv_math` for `derivation_checker`
      as well (caller = executor = `derivation_checker`), for targeted
      identifier lookups only
- [ ] Extend `derivation_checker.yaml` check 5 (citation grounding) as in §6
- [ ] `README_HEP_THEORY.md`: a short section on the new agent and the
      checker's new tools

## 6. derivation_checker: mathematics citation grounding

Today check 5 only compares claims with what `inspirehep_context` reported.
Proposed replacement text for check 5 in `derivation_checker.yaml`:

```
5. **Citation grounding** - for any claim presented as an established result
   (rather than something newly derived in this session):
   - is it consistent with what inspirehep_context and mathlit_context
     reported, or does it contradict a cited source?
   - for every MATHEMATICS citation that a verdict depends on, verify the
     identifier with ONE targeted lookup (search_arxiv_math for an arXiv ID,
     search_zbmath for a zbMATH ID or title): does the paper exist, and do
     its title and authors match the citation?
   - is the stated status right? A result reported as PROVED must not be
     only conjectured, folklore, or a physics derivation.
   You verify; you do not originate new literature searches. If a lookup
   returns a TOOL ERROR, say the citation is unverified.
```

The output line for check 5 gains a short list: each mathematics citation
checked, with VERIFIED / MISMATCH / NOT FOUND / UNVERIFIED (tool error).

## 7. Tests (offline, in tests/regression/)

- Each tool with mocked HTTP: a normal response is formatted correctly; an
  empty response says "no results"; a network error or bad status returns the
  "TOOL ERROR" string and never raises.
- Snippet truncation: abstracts never exceed the limit.
- R10 (allowlists) extended automatically, since it checks every agent folder.
- Routing invariant (R6): `mathlit_context` is on a model that does not need
  forced tool choice.
- Registration: both new tools are registered for `mathlit_context` and
  `derivation_checker`, and for no other agent.
- Bite check for each test, as for the rest of the suite.

## 8. Evaluation (real API calls: credit-funded)

Re-run the fuzzy del Pezzo claim-A novelty step with `mathlit_context` added,
and compare with the 1 October run.

- **Known targets** it should find: Ishii–Ueda (arXiv:0911.4529); Bergman–Proudfoot
  (math/0512166); work on cuts and consistency of dimer models (e.g. Bocklandt).
- **Measures**: recall of the known targets; every cited ID verified; queries
  logged; no paraphrase presented as a quotation (the 1 October checker
  failure). Repeat three times to see variance.
- **Pass condition**: finds at least two of the three targets in a majority of
  runs, with zero fabricated identifiers.
- **Checker test**: plant one wrong mathematics citation (a real arXiv ID
  with the wrong title, or a conjecture labelled PROVED) in a synthetic
  report; `derivation_checker` must flag it. This is the bite check for
  the checker's new role.
- **Later, with credits**: repeat the evaluation with Opus 5.5 for
  `mathlit_context` and compare recall and cost.

## 9. Decisions (5 October 2026)

1. Default arXiv categories include `math-ph`.
2. Model: Sonnet 5.5 for now; consider Opus 5.5 once programme credits arrive,
   using the evaluation above to compare.
3. `derivation_checker` also verifies mathematics citations (§6).
