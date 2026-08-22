# snippetveil.com

The vendor site for [SnippetVeil](https://github.com/snippetveil/snippetveil), a static page
deployed to Cloudflare Pages from `public/`. No build step, no dependencies, no JavaScript.

It exists because the JetBrains Marketplace requires a vendor URL that resolves to real content
over HTTPS, and a broken or empty one is a documented rejection reason.

## Copy rules

The wording here is bound by the same rules as the Marketplace listing, because the strictest
surface wins: no third-party brand references, no marketing adjectives, no unverifiable claims,
English first, HTTPS links only.

The product claims — the *no network* paragraph, the three "does not hide" lines and the three
"does not preserve" lines — are settled elsewhere and are reproduced here **verbatim**. Editing
their wording on this page does not reopen them, and two differently-worded statements of the same
claim are exactly what the verbatim rule exists to prevent. Treat this page as a third surface of
the canonical block, alongside the listing and the product README.

The status note is the one part that is specific to this page: it says the plugin is unpublished
and that the automated no-network checks are not in place yet. **Remove it only when both are no
longer true.**

## Deploying

A Cloudflare Worker serving static assets — the successor to Pages, and where the dashboard's
"Connect to Git" now lands. `wrangler.jsonc` declares `public/` as the asset directory and no
Worker script, so the files are served as-is.

- Build command: none.
- Deploy command: `npx wrangler deploy`.
- Pushing to `main` redeploys.

`_headers` is honoured by Workers static assets, same as it was under Pages.
