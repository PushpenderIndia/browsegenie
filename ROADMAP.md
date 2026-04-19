# Roadmap

This document outlines the planned features and improvements for Universal Scraper.

## Save Token (High Priority)

Test this module against multiple different sites, and for those sites where the reduction percentage is not that great, check the final cleaned html, which is present inside the temp folder, and try implementing a universal cleaner function to reduce the HTML size

## Improve Reliability

- [ ] ⁠Retry Mechanism to re-generate the bs4 code till it is able to generate correct extraction code (beautifulsoup4 code)
- [ ] Captcha Resolve using Third Party api
- [ ] Proxy Rotation
- [ ] Parallel Browser Agents & Scraper Agents

## Extra Features

- [ ] Export data to excel (xslx) for adding formating & styling
    - [ ] Setting Appropriate Width of headers based on maxlenght of column's value
    - [ ] Setting Color (User should have ability to overwrite the default color)
- [ ] Add `min_limit` and `max_limit` parameters to `scrape_url()` method that replaces `DYNAMIC` placeholder with page numbers from min to max range, scrapes each URL sequentially, and aggregates results before saving.

```
e.g.

result = scraper.scrape_url("https://example.com/jobs?page=DYNAMIC", min_limit=1, max_limit=100)
```
