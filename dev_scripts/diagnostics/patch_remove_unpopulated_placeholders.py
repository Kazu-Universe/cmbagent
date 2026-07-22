"""
One-time patch: removes unpopulated template placeholders ({inspirehep_context},
{cadabra_context}) from all three hep-theory agent YAML prompts.

Root cause: these were always forward-looking placeholders meant for actual
RAG-retrieved content (a real INSPIRE-HEP API fetch, apis/inspirehep_search.py)
that was never implemented - flagged explicitly in the original README as a
known gap. Since nothing populates context_variables["inspirehep_context"] or
["cadabra_context"], AG2's system-message template.format(**context) call
raises KeyError the moment any of these three agents is actually invoked.
Confirmed via a real crash on the first real invocation of inspirehep_context.

Fix: remove the placeholder blocks entirely rather than defaulting them to an
empty string, since an empty tag provides no value - the agents' own prose
instructions already tell them how to search/reason without needing an
injected-context block that nothing fills in (yet).

Run once from the repo root:
    python patch_remove_unpopulated_placeholders.py
"""

files_and_blocks = [
    (
        "cmbagent/agents/inspirehep_context/inspirehep_context.yaml",
        "  <RETRIEVED_LITERATURE>\n   {inspirehep_context}\n  </RETRIEVED_LITERATURE>\n",
    ),
    (
        "cmbagent/agents/cadabra_context/cadabra_context.yaml",
        "  <DOCUMENTATION>\n   {cadabra_context}\n  </DOCUMENTATION>\n",
    ),
    (
        "cmbagent/agents/derivation_checker/derivation_checker.yaml",
        "  **Relevant literature context (if any):**\n  {inspirehep_context}\n",
    ),
]

marker = "# hep-theory fork: placeholder removed"

for path, block in files_and_blocks:
    with open(path, "r") as f:
        content = f.read()

    if marker in content:
        print(f"Already patched: {path}")
        continue

    count = content.count(block)
    if count != 1:
        print(f"WARNING: expected exactly 1 occurrence in {path}, found {count}. "
              f"Skipping - check manually.")
        continue

    content = content.replace(block, f"{marker}\n", 1)

    with open(path, "w") as f:
        f.write(content)

    print(f"Patched: {path}")

print("\nDone.")
