# BioMed Article Converter

![Coverage](./badges/coverage.svg)

This is a simple package made to convert NCBI PubMed/PMC XML formats into more common and useable downstream formats such as HTML, MD, or plain text

This can be used as command line tool or as a library. For example to convert the XML from a pmc article to html

```bash
python -m biomed_article_converter input.xml output.html --source_type pmc
```

or via the library to convert to markdown

```python
from biomed_article_converter import convert_format


with open("input.xml", "r") as fh:
    content = fh.read()

md = convert_format("xml", "md", content, source_type="pmc")
```

While the xml to html conversion tries to retain as much information as possible, the simpler md and txt formats make some assumptions on what you want to keep.

By default the md/txt formats drop the following

- author details
- references
- inline citations
- article metadata

as well as any sections with known non-informative titles defined by (OMIT_TITLES)

```python
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
```

## Table Normalization

For markdown or plain text, we cannot support the nested/complex table structures seen in html. Therefore the first step is simplifying the tables. For cells the span multiple columns or rows we simply create X new cells and repeat the content. For multi-row headers were concatenate each header level within a cell by row1: row2: cell content

## XML inspection helpers

`biomed_article_converter` also provides small XML-structure helpers used when working with raw NCBI article responses.

### Split PubMed article sets

PubMed `efetch` responses may contain multiple `PubmedArticle` or `PubmedBookArticle` records. Use `split_articles_from_pubmed_xml()` to split a response into individual XML documents keyed by PMID:

```python
from biomed_article_converter import split_articles_from_pubmed_xml

articles = split_articles_from_pubmed_xml(xml)

article_xml = articles["32214442"]
```

The returned values are standalone XML strings for each article. Both regular PubMed articles and PubMed book articles are supported.

### Detect abstract-only records

Use `is_abstract_only()` to determine whether an article XML record contains only abstract-level content:

```python
from biomed_article_converter import is_abstract_only

if is_abstract_only(xml, source_type="pmc"):
    print("PMC did not provide substantive full text")
```

For PMC/JATS XML, a document is considered abstract-only when it has no substantive `<body>` content. PubMed XML records are abstract-level records by definition, so `source_type="pubmed"` returns `True`.

These helpers inspect article XML structure only; they do not perform format conversion.
