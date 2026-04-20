"""Shared CSS selector constants for the browser-agent tool layer.

Using one source of truth prevents index-skew bugs that occur when the
selector used by click() differs from the one used by get_interactive_elements().
"""

# For Python Playwright calls (e.g. page.query_selector_all)
INTERACTIVE_SEL = (
    "a[href], button, input, select, textarea, "
    "[onclick], [role='button'], [role='link'], [tabindex]"
)

# For embedding inside single-quoted JavaScript strings passed to page.evaluate().
# CSS attribute values use double quotes so they don't break the JS string delimiters.
INTERACTIVE_SEL_JS = (
    "a[href], button, input, select, textarea, "
    '[onclick], [role="button"], [role="link"], [tabindex]'
)
