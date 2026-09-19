# PUBLICATION_TARGETS.md

## Canonical public deployment target

**EXIOR.io is served by the repository `Falcone747/exior-pages`.**

This is the canonical repository for all public EXIOR website pages and vertical publications.

### Hard rule

Do NOT attempt to attach `exior.io` to `Falcone747/EXIOR-`.

- `Falcone747/EXIOR-` = EXIOR system / OS / architecture / operational code.
- `Falcone747/exior-pages` = canonical public website deployment repository for `https://exior.io`.

For every public EXIOR publication:

1. create/update the page in `Falcone747/exior-pages/app/<slug>/`;
2. ensure `.github/workflows/pages.yml` copies it into `_site/<slug>/`;
3. add a build validation for the page;
4. merge to `main`;
5. verify the GitHub Pages workflow;
6. verify the exact public URL on `https://exior.io/<slug>/`.

Never report a page as live before both deployment and public URL verification succeed.
