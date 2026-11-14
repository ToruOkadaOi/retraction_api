"""Small browser entry points for the API and MCP services."""


def _page(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ margin: 0; background: #fff; color: #222;
           font: 17px/1.6 system-ui, sans-serif; }}
    main {{ max-width: 36rem; margin: 12vh auto; padding: 0 1.5rem; }}
    h1 {{ font-size: 1.75rem; line-height: 1.25; letter-spacing: -0.025em; }}
    p {{ margin: 1.25rem 0; }}
    a {{ color: #2455a4; text-underline-offset: 0.2em; }}
    a:focus-visible {{ outline: 2px solid currentColor; outline-offset: 4px; }}
    code {{ font-size: 0.9em; overflow-wrap: anywhere; user-select: all; }}
    footer {{ margin-top: 3rem; font-size: 0.875rem; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    {content}
    <footer><a href="https://github.com/ToruOkadaOi/retraction_api">Source on GitHub</a></footer>
  </main>
</body>
</html>
"""


API_HOMEPAGE = _page(
    "Retraction Watch API",
    """<p>Search the Retraction Watch database for retractions, corrections,
    expressions of concern, and reinstatements.</p>
    <p><a href="/docs">API documentation</a></p>""",
)

MCP_HOMEPAGE = _page(
    "Retraction Watch MCP",
    """<p>Paste this URL into your MCP client.</p>
    <p><code>https://retraction-watch-mcp.onrender.com/mcp</code></p>""",
)
