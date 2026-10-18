# Source and Git-history credential audit

The October 18, 2026 audit found **no credential-pattern or suspicious literal
secret matches** in the fetched LingoLive repository. The audited application
commit is `ad889871fc9583a2dd956d4ad17841e50db431f1`.

The scan covered 37 reachable commits, one additional local commit, 688 Git blob
objects, commit/tag messages, current changed source, and the downloadable web
source ZIP. It decompressed 250 archive members, extracted text from 16 PDFs and
performed English OCR on 78 unique images. There were no incomplete scan items.
The remote advertised one branch (`main`) and no tags at audit time.

Rules include Google API keys, OAuth tokens/codes/client secrets, GitHub tokens,
private keys, AWS access IDs, selected other provider tokens, JWT literals, URL
passwords and high-entropy secret assignments. HTML/URL/Unicode escapes and
selected base64 literals are checked too. Only finding locations and hashes are
reported; credential values are never printed. No credential-verification API
requests are made.

Evidence: `validation/source-secret-audit.json`. Reproduce after fetching all
remote branches/tags:

```sh
python tools/audit_repository_secrets.py --ocr \
  --archive dist/LingoLive-web-source.zip --output /tmp/lingolive-secret-audit.json
```

This is a pattern scan with OCR, not a guarantee against unknown formats,
obfuscation or OCR errors. Inaccessible deleted remote objects, external forks,
caches and untracked private deployment directories are outside the fetched
repository history. Deployment SDK profiles and local private files must never
be packaged. Public examples contain placeholders; test credentials are
synthetic. Real keys, host access codes and operator tokens remain excluded.
