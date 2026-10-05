import argparse
import copy
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

from anyascii import anyascii
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from lxml import etree
from markdown import markdown
from markdownify import MarkdownConverter

OMIT_TITLES = {
    "ethics statement",
    "conflict of interest",
    "conflicts of interest",
    "acknowledgments",
    "acknowledgment",
    "data deposition and access",
    "data availability",
    "code availability",
    "author contributions",
    "funding",
    "competing interest statement",
    "competing interests",
}
OMIT_CLASSES = {
    "metadata-panel",
    "authors-list",
    "affiliations-list",
    "references",
    "article-xref bibr",
    "ext-link",
}
TEMPLATES = {}
H_TAGS_PATT = re.compile(r"^h[1-6]$")
VALID_FORMAT_TYPES = ["xml", "html", "md", "txt"]
REMOVED = "\ue000REMOVED\ue001"
REMOVED_ESC = re.escape(REMOVED)
NBSP_REGEX = re.compile(
    r"\u00a0|\u2009|&(nbsp|thinsp);|&#160;|&#xa0;|&#8201;|&#x2009;", re.IGNORECASE
)

# 1. Compile PMC Template safely with specific XSLT error catching
try:
    pmc_path = str(Path(__file__).parent / "data" / "pmc_mapping.xsl")
    TEMPLATES["pmc"] = etree.XSLT(etree.parse(pmc_path))
except etree.XMLSyntaxError as e:
    raise RuntimeError(f"Your pmc_mapping.xsl file has invalid XML syntax: {e}")
except etree.XSLTParseError as e:
    raise RuntimeError(
        f"Your pmc_mapping.xsl is valid XML, but is NOT a valid XSLT stylesheet: {e}"
    )

# 2. Compile PubMed Template safely with specific XSLT error catching
try:
    pubmed_path = str(Path(__file__).parent / "data" / "pubmed_mapping.xsl")
    TEMPLATES["pubmed"] = etree.XSLT(etree.parse(pubmed_path))
except etree.XMLSyntaxError as e:
    raise RuntimeError(f"Your pubmed_mapping.xsl file has invalid XML syntax: {e}")
except etree.XSLTParseError as e:
    raise RuntimeError(
        f"Your pubmed_mapping.xsl is valid XML, but is NOT a valid XSLT stylesheet: {e}"
    )


@lru_cache(maxsize=4096)
def compile_regex(patt: str, **kwargs) -> re.Pattern:
    return re.compile(patt, **kwargs)


def greek_to_names(text: str) -> str:
    result = []
    for char in text:
        # Check if the character is from the Greek block
        if "GREEK" in unicodedata.name(char, ""):
            # Extract the specific letter name (e.g., "GREEK CAPITAL LETTER OMEGA" -> "OMEGA")
            whole_name = unicodedata.name(char)
            name = whole_name.split()[-1]
            if name == "LAMDA":
                name = "LAMBDA"

            if "CAPITAL" in whole_name:
                name = name.title()
            else:
                name = name.lower()
            result.append(name)
        else:
            result.append(char)
    return "".join(result)


class SafeMarkdownConverter(MarkdownConverter):
    """
    Markdownify escapes too much and then it doesn't convert back to html correctly
    """

    def escape(self, text: str, *args, **kwargs) -> str:
        # Let markdownify do its normal escaping first
        text = super().escape(text, *args, **kwargs)
        # Immediately unescape the equal signs
        text = text.replace(r"\=", "=").replace(r"\~", "~").replace(r"\&", "&")

        # only need to escape < if it is followed by a letter or @
        text = compile_regex(r"\\(<)(?![a-zA-Z@])").sub(r"\1", text)

        return text


def _get_soup(tag: Tag) -> BeautifulSoup:
    node = tag
    while node.parent is not None:
        node = node.parent
    return node


def _remove_cell_newlines(cell: Tag) -> None:
    """Replace in-cell line breaks with spaces and normalize whitespace."""

    # Replace <br> with spaces.
    for br in cell.find_all("br"):
        br.replace_with(" ")

    # Merge adjacent text nodes so inserted spaces cannot be stripped
    # independently during later HTML -> Markdown conversion.
    cell.smooth()

    # Collapse newlines/tabs/repeated whitespace.
    for node in list(cell.descendants):
        if isinstance(node, NavigableString):
            node.replace_with(compile_regex(r"\s+").sub(" ", str(node)))

    cell.smooth()


def collapse_multiline_header(table: Tag) -> None:
    """
    Collapse a multi-row <thead> into one row.

    Header values from each level are joined with ": ".
    Assumes rowspan/colspan have already been flattened.
    """

    thead = table.find("thead", recursive=False)
    if thead is None:
        return

    rows = thead.find_all("tr", recursive=False)

    if len(rows) <= 1:
        return

    cells_by_row = [row.find_all(["th", "td"], recursive=False) for row in rows]

    width = max((len(cells) for cells in cells_by_row), default=0)

    soup = _get_soup(table)
    new_row = soup.new_tag("tr")
    new_row.attrs = copy.deepcopy(rows[0].attrs)

    for col in range(width):
        parts = []
        source_cell = None

        for row_cells in cells_by_row:
            if col >= len(row_cells):
                continue

            cell = row_cells[col]
            text = " ".join(cell.stripped_strings)

            if not text:
                continue

            # Avoid things like "Drug: Drug: Drug" when the original
            # header used rowspan and was duplicated during flattening.
            if parts and text == parts[-1]:
                continue

            parts.append(text)
            source_cell = cell

        new_cell = soup.new_tag("th")

        if source_cell is not None:
            new_cell.attrs = copy.deepcopy(source_cell.attrs)
            new_cell.attrs.pop("rowspan", None)
            new_cell.attrs.pop("colspan", None)

        new_cell.string = " ".join(parts)
        new_row.append(new_cell)

    for row in rows:
        row.extract()

    thead.append(new_row)


def flatten_table(table: Tag) -> None:
    """
    Flatten rowspan/colspan in a BeautifulSoup <table> in place.

    - rowspan content is repeated vertically
    - colspan content is repeated horizontally
    - row/column orientation is preserved
    - resulting cells have no rowspan/colspan attributes
    - multi-row headers are collapsed with ": "
    """

    soup = _get_soup(table)

    rows = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]

    grid = []

    for r, tr in enumerate(rows):
        while len(grid) <= r:
            grid.append([])

        source_cells = tr.find_all(["th", "td"], recursive=False)
        col = 0

        for source_cell in source_cells:
            try:
                rowspan = max(int(source_cell.get("rowspan", 1) or 1), 1)
            except (TypeError, ValueError):
                rowspan = 1

            try:
                colspan = max(int(source_cell.get("colspan", 1) or 1), 1)
            except (TypeError, ValueError):
                colspan = 1

            # Find the next unoccupied position where this colspan fits.
            while True:
                while len(grid[r]) < col + colspan:
                    grid[r].append(None)

                if all(grid[r][c] is None for c in range(col, col + colspan)):
                    break

                col += 1

            # Fill every grid position occupied by this cell.
            for rr in range(r, r + rowspan):
                while len(grid) <= rr:
                    grid.append([])

                while len(grid[rr]) < col + colspan:
                    grid[rr].append(None)

                for cc in range(col, col + colspan):
                    cell = copy.deepcopy(source_cell)
                    cell.attrs.pop("rowspan", None)
                    cell.attrs.pop("colspan", None)
                    _remove_cell_newlines(cell)
                    grid[rr][cc] = cell

            col += colspan

    width = max((len(row) for row in grid), default=0)

    # Rebuild rows in their original order.
    for r, tr in enumerate(rows):
        for cell in tr.find_all(["th", "td"], recursive=False):
            cell.extract()

        for c in range(width):
            cell = grid[r][c] if c < len(grid[r]) else None

            if cell is None:
                tag_name = "th" if tr.find_parent("thead") is not None else "td"
                cell = soup.new_tag(tag_name)

            tr.append(cell)

    collapse_multiline_header(table)


def cleanup_removed_content(text: str) -> str:
    # Sentinel is the only meaningful content inside () or []
    text = compile_regex(rf"\s*[\[(]\s*[,;:\s–-]*{REMOVED_ESC}[,;:\s–-]*[\])]").sub("", text)

    # Sentinel in the middle of a list:
    # (foo, REMOVED, bar) -> (foo, bar)
    # [foo; REMOVED; bar] -> [foo; bar]
    text = compile_regex(rf"([,;])\s*{REMOVED_ESC}\s*([,;])").sub(r"\1", text)

    # Sentinel at end of a list:
    # (foo, REMOVED) -> (foo)
    text = compile_regex(rf"([,;:])\s*{REMOVED_ESC}\s*(?=[\])])").sub("", text)

    # Sentinel at start of a list:
    # (REMOVED, foo) -> (foo)
    text = compile_regex(rf"(?<=[\[(])\s*{REMOVED_ESC}\s*[,;:]\s*").sub("", text)

    # Remove remaining sentinels
    text = text.replace(REMOVED, "")

    # Final spacing normalization
    text = compile_regex(r"\s+([,;?!])(?!\S)").sub(r"\1", text)
    text = compile_regex(r"\s+(\.)(?!\d)").sub(r"\1", text)
    text = compile_regex(r" {2,}").sub(" ", text)

    return text


def prep_html_for_md(html_string: str, omit_titles: set[str], omit_classes: set[str]) -> str:
    omit_titles = [t.lower() for t in omit_titles]
    # 2. Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html_string, "html.parser")

    # 4. Find and completely destroy those tags
    for tag in soup(["title"]):
        tag.decompose()  # .decompose() deletes the tag AND its inner contents

    # Find all tags with the class and destroy them
    for tag in soup.find_all(class_=omit_classes):
        tag.replace_with(REMOVED)

    # these are tags we want to remove the tag itself but keep the content
    for tag in soup.find_all(class_=["article-xref table", "article-xref fig"]):
        tag.unwrap()

    # 2. Iterate through all <section> tags
    for section in soup.find_all("section"):
        # 3. Look only at immediate children matching our h tags
        # recursive=False stops Beautiful Soup from searching deeper inside the section
        heading = section.find(H_TAGS_PATT, recursive=False)

        # 4. Check if the heading exists and has the target text
        if heading and heading.get_text(strip=True).lower() in omit_titles:
            tag.decompose()

    for table in soup.find_all("table"):
        flatten_table(table)

    return NBSP_REGEX.sub(" ", cleanup_removed_content(str(soup)))


def convert_xml_to_html(xml_content: str, template_type: str) -> str:
    # Compiling direct from the explicit code string literal
    xml_root = etree.fromstring(xml_content.encode("utf-8"))
    return str(TEMPLATES[template_type](xml_root))


def convert_html_to_md(html_content: str, omit_titles: list[str], omit_classes: list[str]) -> str:
    html_content = prep_html_for_md(
        html_content, omit_titles=omit_titles, omit_classes=omit_classes
    )
    # strip the title element from the header since it is repeated in the body
    return SafeMarkdownConverter(
        heading_style="ATX",
        escape_misc=True,
        wrap_width=None,
        sub_symbol="<sub>",
        sup_symbol="<sup>",
    ).convert(html_content)


def inject_line_breaks_inplace(soup: BeautifulSoup) -> None:
    """
    Makes the html text more readable with line breaks between major page elements
    """
    # 1. Strip raw single line breaks inside <p> elements
    for p_tag in soup.find_all("p"):
        if isinstance(p_tag, Tag):
            for text_node in p_tag.find_all(string=True):
                if isinstance(text_node, NavigableString):
                    # Replaces any single \n that is neither preceded nor followed by another \n
                    cleaned_text = compile_regex(r"(?<!\n)\n(?!\n)").sub(" ", text_node)
                    text_node.replace_with(cleaned_text)

    # 2. Add structural line breaks after major elements close
    major_page_elements = [
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ol",
        "ul",
        "table",
        "div",
        "blockquote",
    ]

    for element in list(soup.find_all(major_page_elements)):
        if isinstance(element, Tag) and hasattr(element, "insert_after"):
            newline = NavigableString("\n")
            element.insert_after(newline)


def convert_markdown_to_text(md_content: str) -> str:
    # fix for bad md escapes. valid md escapes but markdown library doesn't handle them
    md_content = compile_regex(r"(?<!\\)\\+<").sub("&lt;", md_content)
    md_content = compile_regex(r"(?<!\\)\\+>").sub("&gt;", md_content)
    # convert md back to html
    html_content = markdown(md_content)
    # markdownifys sometimes leaves pipe characters escaped when it shouldnt
    html_content = compile_regex(r"(?<!\\)\\+\|").sub("|", html_content)

    soup = BeautifulSoup(html_content, "html.parser")
    # 2. Find all <sup> tags and replace them with ^text
    for sup in soup.find_all("sup"):
        # Create the new string format you want
        inner_text = sup.get_text().strip()
        if inner_text in {"+", "-"}:
            replacement_text = inner_text
        else:
            replacement_text = f"^{sup.get_text().strip()}"
        # Replace the HTML tag with the new text node
        print("supr replace", inner_text, replacement_text)
        sup.replace_with(replacement_text)

    inject_line_breaks_inplace(soup)
    text = soup.get_text()
    # presub bad anyascii subs
    letter_subs = {
        "™": "(TM)",
        "©": "(c)",
        "→": "->",
        "·": ".",
        "≈": "~=",
        "×": "x",
        "—": "--",
        "∆": "Delta",  # non-greek delta
        "ϵ": "eps",
        "⊥": " perpendicular",
        "∥": " parallel",
        "±": "+/-",
    }
    for original, repl in letter_subs.items():
        text = text.replace(original, repl)

    # use one-letter abbrv for mu if not spaced (ex. umg/ml)
    text = compile_regex(r"μ(?=\w)").sub("u", text)

    # make sure the end result has spaces around deg
    text = compile_regex(r"\s*°\s*").sub(" deg ", text)
    text = greek_to_names(text)

    text = anyascii(text)

    # cleanup whitespace
    text = compile_regex(r"[ ][ ]+").sub(" ", text)
    text = compile_regex(r"[ ]+(\)|\])").sub(r"\1", text)
    text = compile_regex(r"(\(|\[)[ ]+").sub(r"\1", text)
    return text


def _local_name(tag: str) -> str:
    """Return an XML tag name without its namespace."""
    return tag.rsplit("}", 1)[-1]


def split_articles_from_pubmed_xml(xml_content: str | bytes) -> dict[str, str]:
    """Split a PubMed XML article set into individual article XML strings keyed by PMID.

    Supports both ``PubmedArticle`` and ``PubmedBookArticle`` records.
    """
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    root = etree.fromstring(xml_content)
    result: dict[str, str] = {}

    for article in root.iter():
        if _local_name(article.tag) not in {"PubmedArticle", "PubmedBookArticle"}:
            continue

        pmid = next(
            (
                (elem.text or "").strip()
                for elem in article.iter()
                if _local_name(elem.tag) == "PMID" and (elem.text or "").strip()
            ),
            None,
        )
        if pmid is None:
            raise ValueError("PubMed article is missing a PMID")

        result[pmid] = etree.tostring(article, encoding="unicode")

    return result


def is_abstract_only(
    xml_content: str | bytes, source_type: Literal["pmc", "pubmed"] = "pmc"
) -> bool:
    """Return whether article XML contains only an abstract and no substantive body.

    This check is currently defined for PMC/JATS XML. PubMed records are abstract-level
    records by definition and therefore return ``True``.
    """
    if source_type == "pubmed":
        return True
    if source_type != "pmc":
        raise ValueError(f"invalid source_type ({source_type})")

    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")
    root = etree.fromstring(xml_content)

    body = next((elem for elem in root.iter() if _local_name(elem.tag) == "body"), None)
    if body is None:
        return True

    return not any((text or "").strip() for text in body.itertext())


def convert_format(
    input_format: Literal["xml", "html", "md"],
    output_format: Literal["html", "md", "txt"],
    text: str,
    source_type: Literal["pubmed", "pmc"] | None = None,
    html_omit_classes: list[str] = OMIT_CLASSES,
    html_omit_titles: list[str] = OMIT_TITLES,
) -> str:
    """
    Args:
        input_format: The format of the file to be converted
        output_format: the target format of the output file
        text: the input text to be converted
        source_type: For XML only, where the article is from
        html_omit_classes: will remove elements from the HTML with any of the class attributes in this list
        html_omit_titles: will remove section elements from the HTML where the immediatete <h#> tag of the section matches one of these titles (case insensitive)
    """
    if input_format not in VALID_FORMAT_TYPES:
        raise ValueError(f"invalid input_format ({input_format})")
    if output_format not in VALID_FORMAT_TYPES:
        raise ValueError(f"invalid output_format ({output_format})")
    if source_type is None and input_format == "xml":
        raise ValueError(
            "xml input requires source_type to be defined as either pmc or pubmed"
        )
    if input_format == "xml":
        if output_format == "html":
            return convert_xml_to_html(text, source_type)
        if output_format == "md":
            return convert_html_to_md(
                convert_xml_to_html(text, source_type),
                omit_classes=html_omit_classes,
                omit_titles=html_omit_titles,
            )
        if output_format == "txt":
            return convert_markdown_to_text(
                convert_html_to_md(
                    convert_xml_to_html(text, source_type),
                    omit_classes=html_omit_classes,
                    omit_titles=html_omit_titles,
                )
            )

    if input_format == "html":
        if output_format == "md":
            return convert_html_to_md(
                text, omit_classes=html_omit_classes, omit_titles=html_omit_titles
            )
        if output_format == "txt":
            return convert_markdown_to_text(
                convert_html_to_md(
                    text, omit_classes=html_omit_classes, omit_titles=html_omit_titles
                )
            )
    if input_format == "md" and output_format == "txt":
        return convert_markdown_to_text(text)
    raise ValueError(f"invalid conversion from {input_format} -> {output_format}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="path to the input XML file")
    parser.add_argument("--source_type", default="pmc", choices=list(TEMPLATES))
    parser.add_argument("output", help="path to the output HTML file")
    args = parser.parse_args()

    with open(args.input) as fh:
        data = fh.read()

    input_format = args.input.split(".")[-1]
    output_format = args.output.split(".")[-1]
    output = convert_format(input_format, output_format, data, source_type=args.source_type)

    with open(args.output, "w") as fh:
        fh.write(str(output))


if __name__ == "__main__":
    main()
