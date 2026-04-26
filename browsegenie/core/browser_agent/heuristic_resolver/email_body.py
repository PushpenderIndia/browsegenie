"""
Finds the message body / content area inside an email or post composer.
"""
from typing import Optional
from playwright.sync_api import Page

_STRATEGIES = [
    # Gmail uses a contenteditable div, not a textarea
    'div[aria-label="Message Body"]',
    'div[aria-label*="message body" i]',
    '[contenteditable="true"][aria-label*="message" i]',
    '[contenteditable="true"][aria-label*="body" i]',
    # Textarea (many webmail clients)
    'textarea[name="body"]',
    'textarea[name="message"]',
    'textarea[name="content"]',
    'textarea[aria-label*="message" i]',
    'textarea[aria-label*="body" i]',
    'textarea[placeholder*="message" i]',
    'textarea[placeholder*="write" i]',
    # Generic contenteditable body areas
    '[role="textbox"][contenteditable="true"]',
    'div[contenteditable="true"].editable',
    'div[contenteditable="true"][class*="body" i]',
    'div[contenteditable="true"][class*="message" i]',
    'div[contenteditable="true"][class*="editor" i]',
    # IDs
    'textarea#body',
    'textarea#message',
    'div[id*="body" i][contenteditable="true"]',
    # Twitter / social post areas
    '[data-testid="tweetTextarea_0"]',
    '[data-testid="DraftEditorContainer"] [contenteditable="true"]',
    # Rich text editors (common frameworks)
    '.ql-editor',                    # Quill
    '.ProseMirror',                  # TipTap / ProseMirror
    '.DraftEditor-editorContainer [contenteditable="true"]',  # Draft.js
    'iframe.cke_wysiwyg_frame',      # CKEditor (iframe-based)
]


def resolve(page: Page) -> Optional[str]:
    for selector in _STRATEGIES:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return selector
        except Exception:
            continue
    return None
