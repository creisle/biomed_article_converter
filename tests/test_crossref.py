"""Crossref input conversion regression tests."""

import pytest
from lxml import etree

from biomed_article_converter import convert_format, is_abstract_only
from biomed_article_converter.crossref import crossref_to_pmc_xml

JATS = "http://www.ncbi.nlm.nih.gov/JATS1"


def test_crossref_structured_abstract_markdown():
    fragment = f"""<jats:abstract xmlns:jats="{JATS}">
        <jats:sec><jats:title>Background</jats:title>
          <jats:p><jats:italic>ARID1A</jats:italic> is altered.</jats:p>
        </jats:sec>
        <jats:sec><jats:title>Results</jats:title>
          <jats:p>One finding.</jats:p><jats:p>Another finding.</jats:p>
        </jats:sec>
    </jats:abstract>"""
    result = convert_format("xml", "md", fragment, source_type="crossref")
    assert "**Background:**" in result
    assert "*ARID1A* is altered." in result
    assert "**Results:**" in result
    assert "One finding.\n\nAnother finding." in result
    assert result.index("Background") < result.index("Results")


def test_crossref_multiple_paragraph_roots_and_undeclared_prefix():
    fragment = "<jats:p>First paragraph.</jats:p><jats:p>Second paragraph.</jats:p>"
    result = convert_format("xml", "md", fragment, source_type="crossref")
    assert "First paragraph.\n\nSecond paragraph." in result


def test_crossref_normalization_preserves_mathml_namespace():
    fragment = (
        f'<jats:abstract xmlns:jats="{JATS}">'
        '<jats:p>Value <mml:math xmlns:mml="http://www.w3.org/1998/Math/MathML">'
        "<mml:mi>β</mml:mi></mml:math></jats:p></jats:abstract>"
    )
    converted = etree.fromstring(crossref_to_pmc_xml(fragment).encode())
    assert converted.find("front/article-meta/abstract/p") is not None
    assert converted.find(".//{http://www.w3.org/1998/Math/MathML}math") is not None


def test_crossref_abstract_only():
    assert is_abstract_only("<jats:p>Example</jats:p>", source_type="crossref")


def test_crossref_rejects_unsafe_entity_declarations():
    with pytest.raises(etree.XMLSyntaxError):
        crossref_to_pmc_xml(
            '<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><jats:p>&x;</jats:p>'
        )


def test_crossref_empty_abstract():
    with pytest.raises(ValueError, match="empty"):
        crossref_to_pmc_xml("  ")


def test_crossref_omits_aacr_citation_format_block():
    fragment = f"""<jats:abstract xmlns:jats="{JATS}">
        <jats:p>The study cites Smith et al. (2024) in its scientific discussion.</jats:p>
        <jats:p><jats:bold>Citation Format:</jats:bold> First Author. An AACR abstract [abstract]. In: AACR 2025.</jats:p>
        <jats:p>Copyright 2025 AACR.</jats:p>
    </jats:abstract>"""
    result = convert_format("xml", "md", fragment, source_type="crossref")
    assert "The study cites Smith et al. (2024)" in result
    assert "Citation Format" not in result
    assert "First Author" not in result
    assert "Copyright 2025 AACR" not in result


def test_crossref_omits_citation_with_separate_label_and_body():
    fragment = (
        "<jats:p>Final results paragraph.</jats:p>"
        "<jats:p>Citation Format:</jats:p>"
        "<jats:p>Author A, Author B. Abstract nr 123.</jats:p>"
    )
    article = etree.fromstring(crossref_to_pmc_xml(fragment).encode())
    paragraphs = ["".join(p.itertext()).strip() for p in article.findall(".//abstract/p")]
    assert paragraphs == ["Final results paragraph."]


def test_crossref_omits_structured_citation_section():
    fragment = (
        "<jats:sec><jats:title>Results</jats:title><jats:p>Drug response observed.</jats:p></jats:sec>"
        "<jats:sec><jats:title>Citation Format</jats:title><jats:p>A. Author. Meeting proceedings.</jats:p></jats:sec>"
    )
    article = etree.fromstring(crossref_to_pmc_xml(fragment).encode())
    assert "Drug response observed" in " ".join(article.itertext())
    assert "Meeting proceedings" not in " ".join(article.itertext())


def test_crossref_does_not_remove_unrelated_citation_words():
    fragment = (
        "<jats:p>A citation format can vary across publishers.</jats:p>"
        "<jats:p>Prior studies are cited in the results.</jats:p>"
    )
    article = etree.fromstring(crossref_to_pmc_xml(fragment).encode())
    assert len(article.findall(".//abstract/p")) == 2


@pytest.mark.parametrize("output_format", ["html", "md", "txt"])
def test_crossref_inline_trailing_citation(output_format):
    fragment = (
        "<jats:p>Scientific <jats:italic>finding</jats:italic>. "
        "<jats:bold>Citation Format:</jats:bold> Author. AACR proceedings.</jats:p>"
        "<jats:p>Copyright AACR.</jats:p>"
    )
    result = convert_format("xml", output_format, fragment, source_type="crossref")
    assert "Scientific" in result
    assert "finding" in result
    assert "Citation Format" not in result
    assert "Author" not in result
    assert "Copyright" not in result
    if output_format == "md":
        assert "*finding*" in result


@pytest.mark.parametrize("namespace", ["", f' xmlns="{JATS}"'])
def test_crossref_unprefixed_abstract(namespace):
    fragment = f"<abstract{namespace}><title>Abstract</title><p>First.</p><p>Second.</p></abstract>"
    result = convert_format("xml", "md", fragment, source_type="crossref")
    assert result.strip() == "First.\n\nSecond."


@pytest.mark.parametrize("fragment", ["<abstract/>", "<jats:p> </jats:p>", "<!-- empty -->"])
def test_crossref_no_text(fragment):
    with pytest.raises(ValueError, match="no text"):
        crossref_to_pmc_xml(fragment)


def test_crossref_malformed_xml():
    with pytest.raises(etree.XMLSyntaxError):
        crossref_to_pmc_xml("<jats:p>Unclosed")


def test_crossref_cli(tmp_path, monkeypatch):
    from biomed_article_converter import main

    input_path = tmp_path / "abstract.xml"
    output_path = tmp_path / "abstract.md"
    input_path.write_text("<jats:p>Abstract text.</jats:p>")
    monkeypatch.setattr(
        "sys.argv", ["converter", str(input_path), str(output_path), "--source_type", "crossref"]
    )
    main()
    assert output_path.read_text().strip() == "Abstract text."


def test_citation_cleanup_is_crossref_only():
    xml = (
        "<article><front><article-meta><abstract>"
        "<p>Scientific finding.</p><p>Citation Format: Author.</p>"
        "</abstract></article-meta></front></article>"
    )
    assert "Citation Format: Author." in convert_format("xml", "md", xml, source_type="pmc")
    assert "Citation Format" not in convert_format(
        "xml",
        "md",
        "<p>Scientific finding.</p><p>Citation Format: Author.</p>",
        source_type="crossref",
    )


@pytest.mark.parametrize("output_format", ["html", "md", "txt"])
def test_crossref_aacr_bb102_abstract(output_format):
    """Real Crossref abstract for doi:10.1158/1538-7445.AM2024-1963.

    Fixture is the API's verbatim message.abstract, retrieved 2026-10-14,
    including undeclared JATS prefixes and the trailing AACR citation.
    """
    from pathlib import Path

    from bs4 import BeautifulSoup

    fragment = (Path(__file__).parent / "data" / "crossref_AM2024_1963.xml").read_text(
        encoding="utf-8"
    )
    assert "Citation Format: Qi Wang" in fragment
    result = convert_format("xml", output_format, fragment, source_type="crossref")
    labels = ["Introduction:", "Methods:", "Results:", "Conclusion:"]
    positions = [result.index(label) for label in labels]
    assert positions == sorted(positions)
    assert "BB102 only inhibited kinase activity of FGFR4WT, FGFR4N535K and FGFR4V550L" in result
    assert "The phase I study of BB102 is in progress." in result
    for citation_text in ["Citation Format", "Qi Wang", "Proceedings of", "Abstract nr 1963"]:
        assert citation_text not in result
    if output_format == "html":
        # Compare every scientific paragraph, not only selected phrases.
        raw = etree.fromstring(f'<root xmlns:jats="{JATS}">{fragment}</root>'.encode())
        expected = ["".join(p.itertext()) for p in raw.findall(f"{{{JATS}}}p")[:-1]]
        soup = BeautifulSoup(result, "html.parser")
        assert [p.get_text() for p in soup.select("section.abstract p")] == expected
        assert soup.header is None
    else:
        assert result.strip().startswith("Introduction:")
        assert result.strip().endswith("The phase I study of BB102 is in progress.")
