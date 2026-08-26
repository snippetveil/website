# snippetveil.com

The vendor site for [SnippetVeil](https://github.com/snippetveil/snippetveil), a static page
deployed to Cloudflare Pages from `public/`. No build step, no dependencies, no JavaScript.

It exists because the JetBrains Marketplace requires a vendor URL that resolves to real content
over HTTPS, and a broken or empty one is a documented rejection reason.

## Copy rules

The wording here is bound by the same rules as the Marketplace listing, because the strictest
surface wins: no third-party brand references, no marketing adjectives, no unverifiable claims,
English first, HTTPS links only.

The product claims — the *no network* paragraph, the four "does not hide" lines and the two
"does not preserve" lines — are settled elsewhere and are reproduced here **verbatim**. Editing
their wording on this page does not reopen them, and two differently-worded statements of the same
claim are exactly what the verbatim rule exists to prevent. Treat this page as a third surface of
the canonical block, alongside the listing and the product README.

The status note is the one part that is specific to this page. It says the plugin is published and
that the checks behind the *no network* paragraph are in place — both of which are now true, and
both of which have to stay true for the note to stand. **Rewrite it when either changes; do not
delete it.** A page with no status says less than one that states today's.

## Deploying

A Cloudflare Worker serving static assets — the successor to Pages, and where the dashboard's
"Connect to Git" now lands. `wrangler.jsonc` declares `public/` as the asset directory and no
Worker script, so the files are served as-is.

- Build command: none.
- Deploy command: `npx wrangler deploy`.
- Pushing to `main` redeploys.

`_headers` is honoured by Workers static assets, same as it was under Pages.
