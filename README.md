# snippetveil.com

The vendor site for [SnippetVeil](https://github.com/snippetveil/snippetveil), a static page
deployed to Cloudflare Pages from `public/`. No build step, no dependencies, no JavaScript.

It exists because the JetBrains Marketplace requires a vendor URL that resolves to real content
over HTTPS, and a broken or empty one is a documented rejection reason.

## Copy rules

The wording here is bound by the same rules as the Marketplace listing, because the strictest
surface wins: no third-party brand references, no marketing adjectives, no unverifiable claims,
English first, HTTPS links only.

The product claims — the *no network* paragraph, the "does not hide" lines and the "does not
preserve" lines — are settled elsewhere and are reproduced here **verbatim**. Editing their wording
on this page does not reopen them, and two differently-worded statements of the same claim are
exactly what the verbatim rule exists to prevent. Treat this page as a third surface of the canonical
block, alongside the listing and the product README.

**These rules are checked, not remembered.** `.github/workflows/copy-rules.yml` runs
`checks/copy_rules.py` on every push and pull request. It fetches two files from
`snippetveil/snippetveil` at `main`:

- `copy-rules.json` — the banned phrases, roadmap phrases and third-party brand names. None of them
  may appear anywhere in `public/index.html`, and no link may be plain `http`.
- `README.md` — the paragraphs between its `<!-- canonical -->` markers, each of which must appear on
  this page as a paragraph or list item, word for word.

The comparison is on plain text: tags stripped, entities decoded, emphasis unwrapped, whitespace
collapsed. So `<strong>` against `**`, `&mdash;` against `—`, and a wrapped line against one long
one all compare equal. Everything outside the canonical paragraphs — the install line, the status
note, the footer — is this page's own, and changing its words does not fail the check, as long as
any version it names is the current release. Before it reads the page, every run proves the check
against fixture pages: each word on the lists caught, an `http://` link caught, a canonical
paragraph reworded or missing caught, and the page's own words changed passing; and a page naming an
older release, a version with no release, the current release, and the current release without its
`v` — the first two caught, the last two passing.

It also reads the product's releases from the GitHub Releases API. Every release-shaped version
string on the page — `v1.4.0` or `1.4.0`, in the text, an attribute or a link — must be the newest
release that is neither a draft nor a prerelease. Versions are found by pattern, so rewriting the
status note does not break the check and a version added anywhere else is checked too. A failure
says which way the page is wrong: behind the latest release, or naming a release that does not
exist. The Marketplace is not read: it lags manual review, and the page is right as soon as the
release is published.

If the releases cannot be read — GitHub unavailable, or the unauthenticated rate limit reached — the
run fails. A check that goes green without looking would let a stale version through unnoticed. The
failure says *not checked*, names the version the page carries, reports the other rules on their
own, and says to re-run; it names no rule the page breaks.

It reads `main` rather than a pinned ref, deliberately. A phrase added there can turn this repository
red without a commit here. When that happens, the failure names the file it read, where it read it
from, and which rule failed. Fix drift in a canonical paragraph by restoring the settled wording, not
by choosing whichever version reads better.

To run it locally against a checkout of the product repository instead of `main`:
`python3 checks/copy_rules.py --rules ../snippetveil-code/copy-rules.json --readme ../snippetveil-code/README.md`.
Add `--releases releases.json`, a saved response of the releases API, to check offline too.

The status note is the one part that is specific to this page. It names the current release, which
the check above holds to the latest one, so publishing a release turns this repository red until the
note is updated. It says the plugin is published and
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
