"""
Adds tests coverage reporting for the XLST sheets since they are not covered by the normal pytest coverage module
"""

from pathlib import Path

import pytest
from lxml import etree

import biomed_article_converter as parser_module

XSL_NS = {"xsl": "http://www.w3.org/1999/XSL/Transform"}


# ---------------------------------------------------------------------------
# Coverage state
# ---------------------------------------------------------------------------

# Key:
#   (stylesheet_path, match, name, mode)
#
# Value:
#   metadata about the template
_all_templates = {}

# Set of template keys that were executed.
_covered_templates = set()


def _template_id(stylesheet, match, name, mode):
    """Return a unique identifier for an XSLT template."""
    return (str(Path(stylesheet).resolve()), match or None, name or None, mode or None)


# ---------------------------------------------------------------------------
# Stylesheet registration
# ---------------------------------------------------------------------------


def _register_stylesheet(path, seen=None):
    """
    Register all xsl:template elements in a stylesheet.

    Also recursively follows local xsl:include and xsl:import statements.
    """
    path = Path(path).resolve()

    if seen is None:
        seen = set()

    if path in seen:
        return

    seen.add(path)

    tree = etree.parse(str(path))

    for node in tree.xpath("//xsl:template", namespaces=XSL_NS):
        identity = _template_id(path, node.get("match"), node.get("name"), node.get("mode"))

        _all_templates[identity] = {
            "source": path,
            "line": node.sourceline,
            "match": node.get("match"),
            "name": node.get("name"),
            "mode": node.get("mode"),
        }

    # Recursively register included/imported stylesheets.
    for node in tree.xpath("//xsl:include | //xsl:import", namespaces=XSL_NS):
        href = node.get("href")

        if not href:
            continue

        included_path = (path.parent / href).resolve()

        if included_path.exists():
            _register_stylesheet(included_path, seen=seen)


# ---------------------------------------------------------------------------
# Profile handling
# ---------------------------------------------------------------------------


def _profile_template_identity(stylesheet, node):
    """
    Convert a libxslt profile <template> node into one of our template IDs.

    For the primary stylesheet this is straightforward. If an included
    stylesheet contains the same match/name/mode tuple as another stylesheet,
    libxslt's profile does not reliably expose the source file, so we resolve
    against registered templates.
    """
    match = node.get("match") or None
    name = node.get("name") or None
    mode = node.get("mode") or None

    stylesheet = Path(stylesheet).resolve()

    direct = _template_id(stylesheet, match, name, mode)

    if direct in _all_templates:
        return direct

    # Search templates belonging to this stylesheet tree, including includes.
    candidates = [
        identity
        for identity in _all_templates
        if (identity[1] == match and identity[2] == name and identity[3] == mode)
    ]

    if len(candidates) == 1:
        return candidates[0]

    # If ambiguous, prefer the root stylesheet if possible.
    for identity in candidates:
        if identity[0] == str(stylesheet):
            return identity

    # Cannot safely identify the exact source stylesheet.
    return None


def _record_profile(stylesheet, profile):
    """Record all templates executed in one XSLT profile."""
    if profile is None:
        return

    for node in profile.xpath("//template"):
        calls = int(node.get("calls", "0"))

        if calls <= 0:
            continue

        identity = _profile_template_identity(stylesheet, node)

        if identity is not None:
            _covered_templates.add(identity)


# ---------------------------------------------------------------------------
# Transformer proxy
# ---------------------------------------------------------------------------


class XSLTCoverageProxy:
    """
    Proxy around an already-compiled lxml.etree.XSLT object.

    It behaves like the original transformer, but forces profile_run=True
    and records which XSLT templates execute.
    """

    def __init__(self, transform, stylesheet):
        self._transform = transform
        self._stylesheet = Path(stylesheet).resolve()

    def __call__(self, xml, *args, **kwargs):
        # Force profiling on during tests.
        kwargs["profile_run"] = True

        result = self._transform(xml, *args, **kwargs)

        _record_profile(self._stylesheet, result.xslt_profile)

        return result

    def __getattr__(self, name):
        # Preserve access to error_log and other attributes on etree.XSLT.
        return getattr(self._transform, name)


# ---------------------------------------------------------------------------
# Pytest command-line options
# ---------------------------------------------------------------------------


def pytest_addoption(parser):
    group = parser.getgroup("xslt coverage")

    group.addoption("--xslt-cov", action="store_true", help="Report XSLT template coverage")

    group.addoption(
        "--xslt-cov-fail-under",
        type=float,
        default=None,
        metavar="PERCENT",
        help="Fail if XSLT template coverage is below PERCENT",
    )


def _coverage_enabled(config):
    return config.getoption("--xslt-cov") or config.getoption("--xslt-cov-fail-under") is not None


# ---------------------------------------------------------------------------
# Automatically instrument your already-compiled TEMPLATES
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def instrument_xslt(request):
    """
    Replace the already-compiled entries in TEMPLATES with profiling proxies.

    Your normal application code and high-level tests do not need to change.
    """
    if not _coverage_enabled(request.config):
        yield
        return

    data_dir = Path(parser_module.__file__).parent / "data"

    stylesheets = {"pmc": data_dir / "pmc_mapping.xsl", "pubmed": data_dir / "pubmed_mapping.xsl"}

    originals = {}

    for template_name, stylesheet in stylesheets.items():
        stylesheet = stylesheet.resolve()

        if not stylesheet.exists():
            raise RuntimeError(f"Could not find XSLT stylesheet: {stylesheet}")

        if template_name not in parser_module.TEMPLATES:
            raise RuntimeError(f'TEMPLATES does not contain "{template_name}"')

        _register_stylesheet(stylesheet)

        originals[template_name] = parser_module.TEMPLATES[template_name]

        parser_module.TEMPLATES[template_name] = XSLTCoverageProxy(
            originals[template_name], stylesheet
        )

    yield

    # Restore the actual etree.XSLT objects after the test session.
    for template_name, original in originals.items():
        parser_module.TEMPLATES[template_name] = original


# ---------------------------------------------------------------------------
# Coverage calculations
# ---------------------------------------------------------------------------


def _coverage_for_source(source):
    source = Path(source).resolve()

    templates = {identity for identity, info in _all_templates.items() if info["source"] == source}

    covered = templates & _covered_templates

    total_count = len(templates)
    covered_count = len(covered)

    percentage = covered_count / total_count * 100 if total_count else 100.0

    return covered_count, total_count, percentage


def _total_coverage():
    total = len(_all_templates)

    covered = len(set(_all_templates) & _covered_templates)

    percentage = covered / total * 100 if total else 100.0

    return covered, total, percentage


# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _coverage_enabled(config):
        return

    tr = terminalreporter

    tr.write_sep("=", "XSLT coverage")

    if not _all_templates:
        tr.write_line("No XSLT templates found.")
        return

    sources = sorted({info["source"] for info in _all_templates.values()}, key=str)

    for source in sources:
        covered, total, percent = _coverage_for_source(source)

        tr.write_line(f"{source.name}: {covered}/{total} templates covered ({percent:.1f}%)")

    total_covered, total, total_percent = _total_coverage()

    tr.write_line("")
    tr.write_line(f"TOTAL: {total_covered}/{total} templates covered ({total_percent:.1f}%)")

    uncovered = [
        info for identity, info in _all_templates.items() if identity not in _covered_templates
    ]

    if uncovered:
        tr.write_line("")
        tr.write_line("Uncovered templates:")

        uncovered.sort(key=lambda info: (str(info["source"]), info["line"] or 0))

        for info in uncovered:
            attrs = []

            if info["match"]:
                attrs.append(f'match="{info["match"]}"')

            if info["name"]:
                attrs.append(f'name="{info["name"]}"')

            if info["mode"]:
                attrs.append(f'mode="{info["mode"]}"')

            description = " ".join(attrs) or "<anonymous>"

            try:
                source = info["source"].relative_to(Path.cwd())
            except ValueError:
                source = info["source"]

            location = str(source)

            if info["line"]:
                location += f":{info['line']}"

            tr.write_line(f"  {location}: {description}")

    fail_under = config.getoption("--xslt-cov-fail-under")

    if fail_under is not None and total_percent < fail_under:
        tr.write_line("")
        tr.write_line(
            f"FAIL: XSLT coverage {total_percent:.1f}% is below required {fail_under:.1f}%"
        )


# ---------------------------------------------------------------------------
# Fail the pytest run if coverage is too low
# ---------------------------------------------------------------------------


def pytest_sessionfinish(session, exitstatus):
    fail_under = session.config.getoption("--xslt-cov-fail-under")

    if fail_under is None:
        return

    if not _all_templates:
        return

    _, _, percent = _total_coverage()

    if percent < fail_under:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
