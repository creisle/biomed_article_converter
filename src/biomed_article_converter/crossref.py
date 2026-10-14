"""Adapt Crossref JATS abstract fragments to PMC/JATS article XML.

Crossref's REST API returns the ``abstract`` field as an XML fragment, which
may contain a complete ``<jats:abstract>`` or one or more ``<jats:p>`` tags.
"""

import re

from lxml import etree

JATS_NAMESPACE = "http://www.ncbi.nlm.nih.gov/JATS1"
MATHML_NAMESPACE = "http://www.w3.org/1998/Math/MathML"


# AACR conference abstracts often append a bibliographic ``Citation Format:``
# section. It is not part of the scientific abstract itself.
_CITATION_LABEL = re.compile(r"^citation\s+format\s*(?::|$)", re.IGNORECASE)
_INLINE_CITATION_LABEL = re.compile(
    r"(?:^|(?<=[.!?])\s+|\n\s*)citation\s+format\s*:", re.IGNORECASE
)


def _trim_inline_citation(paragraph: etree._Element) -> bool:
    """Trim an appended citation while retaining the paragraph's inline markup."""
    text_nodes = paragraph.xpath(".//text()")
    match = _INLINE_CITATION_LABEL.search("".join(text_nodes))
    if match is None:
        return False
    remaining = match.start()
    for text_node in text_nodes:
        kept = str(text_node)[:remaining]
        remaining = max(0, remaining - len(text_node))
        if text_node.is_tail:
            text_node.getparent().tail = kept
        else:
            text_node.getparent().text = kept
    # Avoid leaving empty formatting elements after the cut.
    for child in reversed(list(paragraph.iterdescendants())):
        if not "".join(child.itertext()).strip() and not (child.tail or "").strip():
            child.getparent().remove(child)
    return True


def _is_citation_block(element: etree._Element) -> bool:
    """Detect a labeled AACR citation block, not ordinary in-text citations."""
    if element.tag == "sec":
        title = next((child for child in element if child.tag == "title"), None)
        return title is not None and bool(_CITATION_LABEL.match(" ".join(title.itertext()).strip()))
    if element.tag in {"p", "title"}:
        contents = " ".join(" ".join(element.itertext()).split())
        return bool(_CITATION_LABEL.match(contents))
    return False


def _remove_trailing_citation(abstract: etree._Element) -> None:
    """Remove the citation label and all following blocks within its parent.

    This operates on the JATS tree rather than finished Markdown, so scientific
    citations in the abstract body are unaffected.
    """
    for parent in (abstract, *abstract.iter("sec")):
        children = list(parent)
        for index, child in enumerate(children):
            if _is_citation_block(child):
                for trailing in children[index:]:
                    parent.remove(trailing)
                break
            if child.tag == "p" and _trim_inline_citation(child):
                for trailing in children[index + 1 :]:
                    parent.remove(trailing)
                break


def _insert_section_heading(section: etree._Element) -> None:
    """Convert a structured JATS section title into a bold paragraph label."""
    title = next((el for el in section if el.tag == "title"), None)
    if title is None:
        return

    heading = "".join(title.itertext()).strip()
    position = section.index(title)
    section.remove(title)
    if not heading:
        return

    first_p = next((el for el in section if el.tag == "p"), None)
    if first_p is None:
        first_p = etree.Element("p")
        section.insert(position, first_p)

    label = etree.Element("bold")
    label.text = heading if heading.endswith((":", ".", "?", "!")) else f"{heading}:"
    label.tail = " " + (first_p.text or "") if len(first_p) or first_p.text else ""
    first_p.text = None
    first_p.insert(0, label)


def crossref_to_pmc_xml(xml_content: str) -> str:
    """Wrap a Crossref abstract XML fragment as an article for the PMC XSLT.

    This is a local conversion only; no Crossref HTTP request is performed.
    JATS paragraph boundaries and inline markup are retained, and structured
    section headings become bold labels at the start of their paragraphs.
    AACR trailing Citation Format sections are omitted.
    """
    if not xml_content.strip():
        raise ValueError("Crossref abstract XML is empty")

    # The fragment may have multiple roots or omit namespace declarations.
    # Disable DTD loading and entity resolution for externally supplied XML.
    fragment = (
        f'<crossref-fragment xmlns:jats="{JATS_NAMESPACE}" '
        f'xmlns:mml="{MATHML_NAMESPACE}">'
        f"{xml_content}</crossref-fragment>"
    )
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    root = etree.fromstring(fragment.encode("utf-8"), parser=parser)

    # PMC's existing XSLT matches *unnamespaced* JATS element names. Leave
    # other namespaces (especially MathML and xlink attributes) untouched.
    for node in root.iter():
        if isinstance(node.tag, str) and etree.QName(node).namespace == JATS_NAMESPACE:
            node.tag = etree.QName(node).localname
    etree.cleanup_namespaces(root)

    abstract = etree.Element("abstract")
    # Crossref can return the abstract element, or the contents of one.
    # Preserve order when the fragment contains multiple paragraphs/sections.
    for element in list(root):
        if element.tag == "abstract":
            if element.text and element.text.strip():
                paragraph = etree.SubElement(abstract, "p")
                paragraph.text = element.text
            for child in list(element):
                abstract.append(child)
        else:
            abstract.append(element)

    if root.text and root.text.strip():
        paragraph = etree.Element("p")
        paragraph.text = root.text
        abstract.insert(0, paragraph)

    _remove_trailing_citation(abstract)

    for section in abstract.iter("sec"):
        _insert_section_heading(section)

    # Top-level abstract titles (usually 'Abstract') aren't part of the text.
    for title in list(abstract):
        if title.tag == "title" and "".join(title.itertext()).strip().lower() == "abstract":
            abstract.remove(title)

    if not any(text.strip() for text in abstract.itertext()):
        raise ValueError("Crossref abstract XML has no text")

    article = etree.Element("article")
    front = etree.SubElement(article, "front")
    metadata = etree.SubElement(front, "article-meta")
    metadata.append(abstract)
    return etree.tostring(article, encoding="unicode")
