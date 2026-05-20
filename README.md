# Weekly Research Digests

Hugo static site hosting three auto-published research digests:
- **MLP weekly** — `content/mlp-weekly/`
- **QMC weekly** — `content/qmc-weekly/`
- **cQED weekly** — `content/cqed-weekly/`

Generated every Monday 09:00 KST by the Hartree agent. This site is a
*defense-in-depth* backup for the Hashnode publications and is treated
as the durable source of truth (git history → static site → CDN).

## Local development

```bash
hugo server -D
# → http://localhost:1313
```

## Publishing a new digest

The Hartree agent calls `publish_hugo.py`:

```bash
python3 publish_hugo.py qmc-weekly drafts/2026-W21.md --verify
```

The script writes to `content/<section>/<slug>.md`, commits, pushes to
`main`, and (with `--verify`) confirms the live URL returns HTTP 200.

## Deployment

`main` push triggers `.github/workflows/deploy.yml`, which builds with
Hugo extended and deploys to GitHub Pages. For Cloudflare Pages, connect
the repo and use:

- Build command: `hugo --minify --gc`
- Output directory: `public`
- Submodules: `recursive`
- Environment variable: `HUGO_VERSION=0.161.1`

## Theme

[PaperMod](https://github.com/adityatelange/hugo-PaperMod) as a git submodule. KaTeX is loaded via `layouts/partials/math.html` for any post with `math: true` in front matter (default on for all posts via `params.math` in `hugo.toml`).
