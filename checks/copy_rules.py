#!/usr/bin/env python3
"""Holds public/index.html to the product repository's copy rules.

The rules are not spelled here. Two files are read from snippetveil/snippetveil at `main`, because
they are two different kinds of fact:

- copy-rules.json: the words no surface may say (banned phrases, roadmap phrases, third-party
  brand names).
- README.md: the paragraphs this page must carry verbatim. They are the ones between the
  `canonical` markers inside its listing-copy block: the *No network* paragraph and the lines of
  the two negative lists. The rest of that block is not canonical, and the page keeps its own
  words for it.

The script reads `main`, not a pinned ref, and that was decided. A phrase added there turns this
repository red without a commit here. The rule is that *no surface says this*, and a page that stays
green on last month's list does not obey it.

Standard library only, so the repository keeps no build system and no dependencies. Every run first
proves that the check can fail (see `self_test`) before it reports that the page passed.
"""

import argparse
import difflib
import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

REPOSITORY = "snippetveil/snippetveil"
REF = "main"
RAW = f"https://raw.githubusercontent.com/{REPOSITORY}/{REF}/"

# The canonical markers are looked for inside the listing-copy block only, which is the one place the
# product build asserts where they are. A marker quoted anywhere else in the README is not the subset.
LISTING_START = "<!-- listing copy -->"
LISTING_END = "<!-- listing copy end -->"
CANONICAL_START = "<!-- canonical -->"
CANONICAL_END = "<!-- canonical end -->"

# The three word lists, as copy-rules.json keys them, with the name a failure reports them under.
WORD_RULES = {
    "bannedPhrases": "banned phrase",
    "roadmapPhrases": "roadmap phrase",
    "thirdPartyBrands": "third-party brand name",
}

# Tags that sit inside a run of text. Every other tag separates words, so `<code>"str1"</code>.`
# reads as `"str1".` with no space before the full stop, the way the Markdown side reads it.
INLINE_TAGS = {"a", "abbr", "b", "code", "em", "i", "kbd", "small", "span", "strong", "sub", "sup", "u", "wbr"}

# Text that is on the page but not in its reading order. A script's text can still be published
# copy — structured data is shown in search results — so it is read for words and links; a template
# is not rendered, so a claim in one does not count as carried. A stylesheet is read for links
# only, because `cursor: pointer` is a property rather than a brand.
SKIPPED_TAGS = {"script", "style", "template"}

# The attributes whose values are shown to a reader, and so are copy. An `href` is not: a URL that
# happens to contain a brand's name is an address, not a reference to the brand. Every attribute
# but a namespace is read for `http://`, because every one of them can point somewhere.
COPY_ATTRIBUTES = {"alt", "aria-description", "aria-label", "content", "label", "placeholder", "title", "value"}


class Failure(Exception):
    pass


class Source:
    """A file the rules were read from, with where it came from, for every failure to name."""

    def __init__(self, name, where, text):
        self.name = name
        self.where = where
        self.text = text


def fetch(name, override):
    if override:
        where = f"{override} (a local override of {REPOSITORY}@{REF}:{name})"
        try:
            return Source(name, where, Path(override).read_text("utf-8"))
        except OSError as error:
            raise Failure(f"Could not read {where}: {error}. Nothing was checked.")
    url = RAW + name
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return Source(name, url, response.read().decode("utf-8"))
    except Exception as error:
        raise Failure(f"Could not read {name} from {url}: {error}. Nothing was checked.")


def collapse(text):
    return re.sub(r"\s+", " ", text).strip()


def markdown_text(markdown):
    """One paragraph or list item of the README, as the plain text a reader sees.

    The product's renderer refuses any `*` or backtick it does not consume as a marker, so every
    one left in the README is a marker and can go.
    """
    return collapse(re.sub(r"[*`]", "", markdown))


class Page(HTMLParser):
    """A page read as: the text of every <p> and <li>, its visible text, the text it does not show
    in reading order, and its attributes."""

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.attributes = []
        self.unrendered = []  # script and template text
        self.stylesheets = []
        self._text = []
        self._open = []  # [tag, parts] for every <p> and <li> still open
        self._skipped = []  # the SKIPPED_TAGS the parser is inside, innermost last
        self.feed(source)
        self.close()
        while self._open:
            self._finish(len(self._open) - 1)
        self.text = collapse(" ".join(self._text))

    def _append(self, data):
        self._text.append(data)
        for _, parts in self._open:
            parts.append(data)

    def _finish(self, index):
        for _, parts in reversed(self._open[index:]):
            self.elements.append(collapse("".join(parts)))
        del self._open[index:]

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            # A namespace is an identifier, not a link: `xmlns="http://www.w3.org/2000/svg"` is
            # the only spelling SVG accepts, and nothing fetches it.
            if value is not None and name != "xmlns" and not name.startswith("xmlns:"):
                self.attributes.append((tag, name, value))
        if tag in SKIPPED_TAGS:
            self._skipped.append(tag)
            return
        if self._skipped:
            return
        if tag not in INLINE_TAGS:
            self._append(" ")
        if tag in ("p", "li"):
            self._open.append([tag, []])

    def handle_endtag(self, tag):
        if tag in SKIPPED_TAGS:
            if tag in self._skipped:
                del self._skipped[len(self._skipped) - 1 - self._skipped[::-1].index(tag):]
            return
        if self._skipped:
            return
        if tag not in INLINE_TAGS:
            self._append(" ")
        if tag in ("p", "li"):
            for index in range(len(self._open) - 1, -1, -1):
                if self._open[index][0] == tag:
                    self._finish(index)
                    break

    def handle_data(self, data):
        if not self._skipped:
            self._append(data)
        elif self._skipped[-1] == "style":
            self.stylesheets.append(data)
        else:
            self.unrendered.append(data)


def canonical_units(readme):
    """The paragraphs and list items between the README's canonical markers, as plain text.

    Headings are skipped: the page is allowed its own heading markup and level, and the claims are
    the sentences under them.
    """
    listing_start = readme.text.find(LISTING_START)
    listing_end = readme.text.find(LISTING_END)
    if listing_start < 0 or listing_end <= listing_start:
        raise Failure(
            f"{readme.where} has no listing-copy block between `{LISTING_START}` and `{LISTING_END}`, "
            "so there is nothing to hold this page to. Rule: canonical paragraphs."
        )
    listing = readme.text[listing_start + len(LISTING_START):listing_end]
    start = listing.find(CANONICAL_START)
    end = listing.find(CANONICAL_END)
    if start < 0 or end <= start:
        raise Failure(
            f"{readme.where} does not mark its canonical paragraphs between `{CANONICAL_START}` and "
            f"`{CANONICAL_END}` inside the listing copy, so there is nothing to hold this page to. "
            "Rule: canonical paragraphs."
        )
    block = listing[start + len(CANONICAL_START):end]
    units = []
    for chunk in re.split(r"\n[ \t]*\n", block.strip()):
        lines = chunk.strip().splitlines()
        if not lines:
            continue
        if lines[0].startswith("#"):
            # The product's renderer refuses a heading with anything under it on the next line, so
            # this cannot pass its build. Refused here too, rather than dropping the claim with the
            # heading.
            if len(lines) > 1:
                raise Failure(f"{readme.where} has a canonical heading with text on the line below it: {chunk!r}")
            continue
        if lines[0].startswith("- "):
            items = []
            for line in lines:
                if line.startswith("- "):
                    items.append(line[2:])
                else:
                    items[-1] += " " + line.strip()
            units.extend(markdown_text(item) for item in items)
        else:
            units.append(markdown_text(" ".join(lines)))
    if not units:
        raise Failure(f"The canonical block in {readme.where} is empty. Nothing was checked.")
    return units


def word_pattern(entry):
    """Whole-word, case-insensitive, and rejoined on whitespace, as the Gradle rules match."""
    return re.compile(r"\b" + r"\s+".join(re.escape(word) for word in entry.split(" ")) + r"\b", re.IGNORECASE)


def label(unit):
    words = unit.split(" ")
    return " ".join(words[:8]) + (" …" if len(words) > 8 else "")


def violations_in(page_html, rules, units):
    """Every copy rule this page breaks, each one naming the rule that caught it."""
    page = Page(page_html)
    violations = []

    copy = " ".join(
        [page.text]
        + page.unrendered
        + [value for _, name, value in page.attributes if name in COPY_ATTRIBUTES]
    )
    for key, name in WORD_RULES.items():
        for entry in rules[key]:
            if word_pattern(entry).search(copy):
                violations.append((key, f"{name}: the page says \"{entry}\""))

    plaintext = re.compile(r"http://[^\s\"'<>()]*", re.IGNORECASE)
    reported = set()
    for tag, attribute, value in page.attributes:
        for match in plaintext.finditer(value):
            reported.add(match.group(0).lower())
            violations.append(("https", f"<{tag} {attribute}=\"{value}\"> is not HTTPS"))
    for text in [page.text] + page.unrendered + page.stylesheets:
        for match in plaintext.finditer(text):
            # A link whose text is its own address is one plaintext link, not two.
            if match.group(0).lower() not in reported:
                reported.add(match.group(0).lower())
                violations.append(("https", f"the page links {match.group(0)}, which is not HTTPS"))

    for number, unit in enumerate(units, start=1):
        if unit in page.elements:
            continue
        closest = difflib.get_close_matches(unit, page.elements, n=1, cutoff=0.6)
        if closest:
            violations.append((
                "canonical",
                f"canonical paragraph {number} is reworded — \"{label(unit)}\"\n"
                f"      settled:   {unit}\n"
                f"      this page: {closest[0]}",
            ))
        else:
            violations.append(("canonical", f"canonical paragraph {number} is absent — \"{label(unit)}\"\n      settled:   {unit}"))

    return violations


# ---------------------------------------------------------------------------------------------------
# The red path, run before the real page is read.
# ---------------------------------------------------------------------------------------------------

# Each row is one way the same sentence is spelled in Markdown and in HTML. A comparison that read
# either spelling differently would report drift that is not there, and a check that cries drift on
# formatting gets switched off.
NORMALISER_FIXTURE = [
    ("bold", "**Your stack.** Frameworks", "<strong>Your stack.</strong> Frameworks"),
    ("italic", "value *is* the algorithm", "value <em>is</em> the algorithm"),
    ("code before a full stop", 'becomes `"str1"`.', "becomes <code>\"str1\"</code>."),
    ("entity", "persistence layer — preserved", "persistence layer &mdash; preserved"),
    (
        "wrapping",
        "SnippetVeil makes no network calls. No networking code — enforced on every pull request, scanned in every release build.",
        "SnippetVeil makes no network calls. No networking code — enforced on every pull request,\n"
        "  scanned in every release build.",
    ),
    ("soft break", "it is not anonymized at all", "it is not anony<wbr>mized at all"),
]


def fixture_page(units, before="", after="", replace_index=None, replacement=None, omit=None):
    """A page carrying every canonical unit, built from the README rather than typed a second time.

    Each unit is spelled the way a hand-written page spells it — the dash as an entity, the text
    wrapped — so the cases below run through the same normaliser the real page does.
    """

    def spelled(unit):
        text = html.escape(unit, quote=False).replace("—", "&mdash;")
        words = text.split(" ")
        return "\n    ".join(" ".join(words[i:i + 9]) for i in range(0, len(words), 9))

    items = []
    for index, unit in enumerate(units):
        if index == omit:
            continue
        items.append(f"  <li>{spelled(replacement if index == replace_index else unit)}</li>")
    return (
        "<!doctype html><html><head><title>SnippetVeil</title></head><body>\n"
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect x="0"/></svg>\n'
        "<p>The site's own words: install it from <strong>Settings → Plugins</strong>.</p>\n"
        f"{before}<ul>\n" + "\n".join(items) + f"\n</ul>\n{after}</body></html>"
    )


def self_test(rules, units, sources):
    """Proves the check can fail, and fails for the right reason, before it is trusted.

    A comparison whose red path is never exercised decays into a check that always passes.
    """
    problems = []

    for row, markdown, markup in NORMALISER_FIXTURE:
        read_markdown = markdown_text(markdown)
        read_html = Page(f"<p>{markup}</p>").elements
        if read_html != [read_markdown]:
            problems.append(f"the normaliser reads the {row} row as {read_html} in HTML and {read_markdown!r} in Markdown")
    if Page("<p>Your stack!</p>").elements == [markdown_text("**Your stack.**")]:
        problems.append("the normaliser called two different sentences equal")

    def kinds(page_html):
        return [key for key, _ in violations_in(page_html, rules, units)]

    clean = fixture_page(units)
    if kinds(clean):
        problems.append(f"a page breaking no rule was flagged: {violations_in(clean, rules, units)}")

    for key in WORD_RULES:
        for entry in rules[key]:
            if kinds(fixture_page(units, after=f"<p>It is {html.escape(entry)} here.</p>\n")) != [key]:
                problems.append(f"the {WORD_RULES[key]} \"{entry}\" was not caught, or not caught alone")
            if kinds(fixture_page(units, after=f'<script type="application/ld+json">{{"d": "{entry}"}}</script>\n')) != [key]:
                problems.append(f"the {WORD_RULES[key]} \"{entry}\" in structured data was not caught")

    # A name in an address or a stylesheet is not copy: `…/spring-guide`, `cursor: pointer`.
    addresses = "".join(f'<a href="https://example.com/{entry.replace(" ", "-")}-guide">a guide</a>' for entry in rules["thirdPartyBrands"])
    stylesheet = "<style>" + " ".join(f".x {{ {entry.lower().replace(' ', '-')}: 1 }}" for entry in rules["thirdPartyBrands"]) + "</style>"
    if kinds(fixture_page(units, after=f"<p>{addresses}</p>{stylesheet}\n")):
        problems.append("a brand name inside a URL or a CSS property was flagged as copy")

    for name, link in [
        ("an http:// link whose text is its address", '<p><a href="http://example.com/">http://example.com/</a></p>'),
        ("a script loaded over http://", '<script src="http://example.com/a.js"></script>'),
        ("a stylesheet importing over http://", "<style>@import url(http://example.com/a.css);</style>"),
    ]:
        if kinds(fixture_page(units, after=link + "\n")) != ["https"]:
            problems.append(f"{name} was not caught exactly once")

    reword_index = len(units) // 2
    reworded = violations_in(
        fixture_page(units, replace_index=reword_index, replacement=" ".join(units[reword_index].split(" ")[:-1] + ["differently."])),
        rules,
        units,
    )
    expected = f"canonical paragraph {reword_index + 1} is reworded"
    if len(reworded) != 1 or not reworded[0][1].startswith(expected):
        problems.append(f"a reworded canonical paragraph was not reported as {expected!r}: {reworded}")

    # The unit least like any other, so that "absent" cannot be mistaken for a rewording of a
    # neighbour however the canonical lines are worded.
    def likeness(index):
        return max((difflib.SequenceMatcher(None, units[index], other).ratio() for i, other in enumerate(units) if i != index), default=0)

    omit_index = min(range(len(units)), key=likeness)
    expected = f"canonical paragraph {omit_index + 1} is absent"
    for name, page_html in [
        ("missing", fixture_page(units, omit=omit_index)),
        ("only in a <template>", fixture_page(units, omit=omit_index, after=f"<template><p>{html.escape(units[omit_index])}</p></template>\n")),
    ]:
        absent = violations_in(page_html, rules, units)
        if len(absent) != 1 or not absent[0][1].startswith(expected):
            problems.append(f"a canonical paragraph {name} was not reported as {expected!r}: {absent}")

    # The one that matters most. A check that fails when the site edits its own words gets turned off.
    edited = fixture_page(units, before="<p>A status note this page wrote for itself.</p>\n").replace(
        "install it from", "get it from"
    )
    if kinds(edited):
        problems.append(f"changing the page's own non-canonical words was flagged: {violations_in(edited, rules, units)}")

    if problems:
        raise Failure(
            "The check failed its own red path, so what it would report about the page is unknown. It read:\n"
            + "".join(f"  {source.where}\n" for source in sources)
            + "\n".join(f"  {problem}" for problem in problems)
        )


def word_rules(source):
    try:
        rules = json.loads(source.text)
    except ValueError as error:
        raise Failure(f"{source.where} is not JSON: {error}. Nothing was checked.")
    for key in WORD_RULES:
        entries = rules.get(key)
        if not isinstance(entries, list) or not entries or not all(isinstance(entry, str) for entry in entries):
            raise Failure(f"{source.where} carries no non-empty `{key}` list. Rule not checked: {WORD_RULES[key]}s.")
    return rules


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--page", default=str(root / "public" / "index.html"))
    parser.add_argument("--rules", help="read copy-rules.json from this path instead of fetching it")
    parser.add_argument("--readme", help="read README.md from this path instead of fetching it")
    arguments = parser.parse_args()

    try:
        rules_source = fetch("copy-rules.json", arguments.rules)
        readme_source = fetch("README.md", arguments.readme)
        rules = word_rules(rules_source)
        units = canonical_units(readme_source)
        self_test(rules, units, [rules_source, readme_source])

        page_path = Path(arguments.page)
        violations = violations_in(page_path.read_text("utf-8"), rules, units)
    except Failure as failure:
        print(f"::error::{str(failure).splitlines()[0]}", file=sys.stderr)
        print(failure, file=sys.stderr)
        return 1

    page_name = page_path.relative_to(root) if page_path.is_relative_to(root) else page_path
    read_from = (
        f"  word lists:           {rules_source.where}\n"
        f"  canonical paragraphs: {readme_source.where}"
    )
    if violations:
        def rule(key):
            if key == "canonical":
                return f"canonical paragraphs, {readme_source.name}"
            if key == "https":
                return "https-only links"
            return f"{key}, {rules_source.name}"

        print(f"::error::{page_name} breaks {len(violations)} copy rule(s) read from {REPOSITORY}@{REF}", file=sys.stderr)
        print(f"{page_name} breaks the product's copy rules, read from:\n{read_from}\n", file=sys.stderr)
        for key, message in violations:
            print(f"  [{rule(key)}] {message}", file=sys.stderr)
        if not (arguments.rules and arguments.readme):
            print(
                f"\nThese rules are read from {REPOSITORY}'s `{REF}`, not a pinned ref: a rule added there applies\n"
                "here without a commit in this repository, which is why this can go red on a page nobody touched.",
                file=sys.stderr,
            )
        print(
            "A canonical paragraph is fixed by restoring the settled wording, not by rewording the README.",
            file=sys.stderr,
        )
        return 1

    print(f"{page_name} keeps every copy rule, read from:\n{read_from}")
    print(
        f"Checked: {sum(len(rules[key]) for key in WORD_RULES)} phrases and names "
        f"({', '.join(f'{len(rules[key])} {key}' for key in WORD_RULES)}), https-only links, "
        f"and {len(units)} canonical paragraphs verbatim."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
