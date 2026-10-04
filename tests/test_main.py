import os
from functools import lru_cache

import pytest
from lxml import etree

from article_converter import convert_format, convert_markdown_to_text


@lru_cache(maxsize=4096)
def read_test_xml(file_id):
    filename = os.path.join(os.path.dirname(__file__), f"data/{file_id}.xml")
    with open(filename) as fh:
        return fh.read()


@pytest.mark.parametrize(
    "file_id,output_format,expected_phrases",
    [
        ("32214442", "html", "<strong>Purpose:</strong>"),
        (
            "34307865",
            "html",
            ["<em>R</em> <sup>2</sup>"],
        ),  # pubmed version does have a space there in the XML
        ("PMC8279135", "html", ["<em>R</em><sup>2</sup>"]),
        (
            "30514790",
            "html",
            [
                '<section class="keywords-section"><strong>Keywords: </strong>lung adenocarcinoma</section>'
            ],
        ),
        (
            "PMC6371742",
            "html",
            [
                '<section class="keywords-section"><strong>Keywords: </strong>lung adenocarcinoma</section>'
            ],
        ),
        (
            "32214442",
            "md",
            [
                "# The SUP-ICU Trial: Does It Confirm or Condemn the Practice of Stress Ulcer Prophylaxis?"
            ],
        ),
        (
            "34307865",
            "md",
            ["*R* <sup>2</sup>"],
        ),  # pubmed version does have a space there in the XML
        ("PMC8279135", "md", ["*R*<sup>2</sup>"]),
        ("30514790", "md", ["**Keywords:** lung adenocarcinoma"]),
        ("PMC6371742", "md", ["**Keywords:** lung adenocarcinoma"]),
        ("PMC6371742", "txt", ["Keywords: lung adenocarcinoma"]),
        ("PMC6371742", "txt", ["\n\nCONCLUSION\n\n"]),
        ("34307865", "txt", [" evaluation.\n\n", "R ^2"]),
        (
            "16442484",
            "md",
            [
                "# Hypnosis for procedure-related pain and distress in pediatric cancer patients: a systematic review of effectiveness and methodology related to hypnosis interventions."
            ],
        ),
        ("17102082", "html", ["(F-, n=42)", "(F+, n=3)"]),
        ("17102082", "md", ["(F-, n=42)", "(F\\+, n=3)"]),
        ("17102082", "txt", ["(F-, n=42)", "(F+, n=3)"]),
        ("PMC4144824", "txt", ["Ibrutinib\n\nBACKGROUND"]),
        ("20628391", "txt", ["combination therapy.\n\nBACKGROUND"]),
        ("PMC3706745", "txt", ["Macroscopically, Braf^V637E-induced neoplasia"]),
        ("PMC8466798", "txt", ["led to the death of ~2 million pigs"]),
        (
            "PMC3203921",
            "md",
            [
                """\
**Table 1:** Summary of ERBB2 mutants analyzed along with the IC50 values
against reversible inhibitors lapatinib and AEE788.

| ERBB2 mutation | Exon | Functional region | Cancer type | Lapatinib | AEE788 | Reference |
| --- | --- | --- | --- | --- | --- | --- |
| WT | NA | NA | Breast cancer | 30 | 257 | NA |
| L755S | 19 | ATP binding region | Breast and gastric cancer | \\>2000 | 897 | 4 |"""
            ],
        ),
        ("PMC3203921", "txt", [" >2000 | 897 | 4 |"]),
        (
            "PMC5029658",  # row-span/col-span cells
            "md",
            [
                "| Cell line | Observed mutation from this study | Variants observed by others | Disease observed in | Reported resistance phenotype | Reference |",
                "| --- | --- | --- | --- | --- | --- |",
                "| SUP-CR500-2 | I1171S | I1171S | NPM-ALK ALCL | ASP-3026-R",
                "| Cell line | Observed mutation from this study | Variants observed by others | Disease observed in | Reported resistance phenotype | Reference |\n| --- | --- | --- | --- | --- | --- |\n| SUP-CR500-2 | I1171S | I1171S | NPM-ALK ALCL | ASP-3026-R",
                "| SUP-CR500-2 | I1171S | I1171T | NPM-ALK ALCL | Crizotinib-R Ceritinib-R Alectinib-R AP26113-R ASP3026-R |",
                "| SUP-CR500-2 | I1171S | I1171H | EML4-ALK NSCLC | Crizotinib-R |",
                """\
| FL5.12 EML4-ALK WT IC50 | FL5.12 EML4-ALK WT Fold Change | FL5.12 EML4-ALK I1171S IC50 | FL5.12 EML4-ALK I1171S Fold Change | """,
            ],
        ),
        ("PMC4902179", "md", ["TCGA-BR-4370-01 | Stomach (TCGA) | R2193C"]),
        ("PMC4453841", "md", ["*GSTP1* Ile<sub>105</sub>Val (rs1695)"]),
        ("PMC4453841", "txt", ["GSTP1 Ile105Val (rs1695)"]),
        (
            "PMC5344332",
            "md",
            [
                "but not by the equivalent construct bearing the *cic*<sup>*4*</sup> lesion (constructs 4 and 5)"
            ],
        ),
        (
            "PMC4253406",
            "txt",
            [
                "previously reported cell lines (CAL27, CAL33, Detroit 562, UM-SCC-47, SCC-25, SCC-9, UM-SCC-11B and UM-SCC-17B), while"
            ],
        ),
        (
            "PMC1702556",
            "txt",
            ["0.8 mM dNTPs, 1 mM MgCl2, 0.2 U", "post-transfection, filtered (0.45 uM)"],
        ),
        ("PMC1702556", "md", ["DNA Analyzer (Applied Biosystems)."]),
        (
            "PMC1702556",
            "html",
            [
                'DNA Analyzer (Applied Biosystems, <a class="ext-link" href="http://www.appliedbiosystems.com">http://www.appliedbiosystems.com</a>).'
            ],
        ),
        ("PMC1423144", "html", ["immunization. [3H]Thymidine"]),
        ("PMC1423144", "md", ["immunization. \\[3H\\]Thymidine"]),
        ("PMC1423144", "txt", ["immunization. [3H]Thymidine"]),
        # weird superscript variant notation in XML
        (
            "PMC4049792",
            "txt",
            [
                "Compared with KRAS wild type and empty vector controls, KRAS 10G11 and 11GA12 significantly enhanced"
            ],
        ),
        # Labelling Abstract sections
        (
            "26161928",
            "txt",
            [
                "AIM: To investigate the impact of KRAS mutation variants on the activity of regorafenib in SW48 colorectal cancer cells."
            ],
        ),
        # more weird superscript notation for SNVs
        (
            "PMC5846801",
            "html",
            [
                "FGFR3 in the ternary complex for the FGFR3<sup>WT</sup>, FGFR3<sup>E466K</sup>, FGFR3<sup>I538F</sup>, FGFR3<sup>N540K</sup>, and FGFR3<sup>K650E</sup>."
            ],
        ),
        # TODO: should the text version of above be a space? currently just FGFR3^WT
        ("17172831", "txt", [" < 0.001). In contrast"]),
        # decimals w/o leading 0
        ("17398248", "txt", [" .80+/-.18 m/s to .96+/-.24 m/s, P<.01; and from"]),
        # lt escaping
        ("18391746", "txt", ["(<50%) nuclear staining. "]),
        # nested + chars
        ("20308656", "txt", ["High EVI1 levels (EVI1(+)) were found"]),
        # arrow notation already in plain text format
        ("19650409", "txt", ["monosomy 3p (pter-->p25) and"]),
        # actual valid (-) in original
        ("16384925", "txt", ["and the c-KIT(-) patients."]),
        # nested brackets
        (
            "17957027",
            "txt",
            [
                "using both markers identified 3 prognostic groups: good (FLT3/ITD(-)NPM1(+)), intermediate (FLT3/ITD(-)NPM1(-)"
            ],
        ),
        ("22705007", "html", ["BACKGROUND &amp; AIMS"]),
        ("22705007", "md", ["BACKGROUND & AIMS"]),
        ("22705007", "txt", ["BACKGROUND & AIMS"]),
        # superscript +/- sign only
        ("27252418", "txt", ["treatment of ER+ advanced breast cancer"]),
        # lots of weird superscripts
        (
            "32360551",
            "md",
            [
                r"We performed studies with Ptf1a<sup>Cre</sup>; Kras<sup>G12D</sup>; Setdb1<sup>f/f</sup>, Ptf1a<sup>Cre</sup>; Kras<sup>G12D</sup>; Trp53<sup>f/\+</sup>; Setdb1<sup>f/f</sup>, and Ptf1a<sup>Cre</sup>; Kras<sup>G12D</sup>; Trp53<sup>f/f</sup>; Setdb1<sup>f/f</sup> mice to investigate the effects "
            ],
        ),
        # keeps punctuation insidebr brackets when present in  XML
        (
            "36866832",
            "txt",
            [
                "PEST domain (NM_017617.4: c.[6626_6629del];[=], p.(Tyr2209CysfsTer38)) and extensive cardiovascular abnormalities consistent"
            ],
        ),
        ("29394989", "txt", ["73 had ?95% probability"]),
        ("31558800", "md", ["BRAF<sup>ΔE1</sup>"]),
        ("31558800", "txt", ["BRAF^DeltaE1"]),
        ("30132220", "md", [" 6,331 'p53-positive (\\+) TNBC' patients "]),
        ("30132220", "txt", [" 6,331 'p53-positive (+) TNBC' patients "]),
    ],
)
def test_convert(file_id, output_format, expected_phrases):
    content = read_test_xml(file_id)

    html = convert_format(
        "xml", "html", content, input_source_type="pmc" if file_id.startswith("PMC") else "pubmed"
    )
    md = convert_format("html", "md", html)
    assert md == convert_format(
        "xml", "md", content, input_source_type="pmc" if file_id.startswith("PMC") else "pubmed"
    )
    assert md == convert_format("html", "md", html)
    text = convert_format("md", "txt", md)
    assert text == convert_format(
        "xml", "txt", content, input_source_type="pmc" if file_id.startswith("PMC") else "pubmed"
    )
    assert text == convert_format("html", "txt", html)
    assert text == convert_format("md", "txt", md)

    final_text = {"html": html, "md": md, "txt": text}[output_format]

    print(repr(final_text))
    for phrase in expected_phrases:
        assert phrase in final_text


@pytest.mark.parametrize(
    "input_format,output_format",
    [
        ("html", "html"),
        ("html", "xml"),
        ("md", "html"),
        ("md", "md"),
        ("md", "xml"),
        ("txt", "html"),
        ("txt", "md"),
        ("txt", "xml"),
        ("txt", "txt"),
        ("xml", "xml"),
        ("xml", "blargh"),
        ("blargh", "xml"),
    ],
)
def test_bad_conversions(input_format, output_format):
    with pytest.raises(ValueError):
        convert_format(input_format, output_format, "")


@pytest.mark.parametrize(
    "input,output,source_type",
    [("input.xml", "output.xml", "pmc"), ("input.xml", "output.html", "other")],
)
def test_main_invalid_args(monkeypatch, input, output, source_type):
    monkeypatch.setattr("sys.argv", [input, output, "--source_type", source_type])

    from article_converter import main

    # argparse will call sys.exit() when validation fails
    with pytest.raises(SystemExit):
        main()


@pytest.mark.parametrize(
    "pmid,md_content,text_content",
    [
        (
            "38749501",
            "Context.—: Pediatric B-cell acute lymphoblastic leukemia",
            "Context.--: Pediatric B-cell acute lymphoblastic leukemia",
        ),
        (
            "31391294",
            r"median depth of \>500× for all coding exons",
            "median depth of >500x for all coding exons",
        ),
        # approx ewuals sign
        (
            "30030733",
            "NSCLC showed that during up to ≈ 19 months' follow-up",
            "NSCLC showed that during up to ~= 19 months' follow-up",
        ),
        # deg
        ("20978130", "(ΔT(m) = 4.8 ∼ -46.8 °C)", "(DeltaT(m) = 4.8 ~ -46.8 deg C)"),
        # arrow cahracters
        ("20034980", "G → C", "G -> C"),
        # beta
        ("22294718", "GSK3β,", "GSK3beta,"),
        (
            "24595080",
            "Patients aged ⩾ 70 years received single agent chemotherapy",
            "Patients aged >= 70 years received single agent chemotherapy",
        ),
        (
            "21575616",
            "AutoGenomics INFINITI® assay, on DNA extracted",
            "AutoGenomics INFINITI(R) assay, on DNA extracted",
        ),
        # non-std period char
        (
            "23122784",
            "29 patients had an objective CNS response (65·9%, 95% CI 50·1-79·5); all were partial responses",
            "29 patients had an objective CNS response (65.9%, 95% CI 50.1-79.5); all were partial responses",
        ),
        # escaped pipe chars
        (
            "30659304",
            "The HER2 status (IHC score\\|HER2-to-CEP17 ratio by FISH testing) of",
            "The HER2 status (IHC score|HER2-to-CEP17 ratio by FISH testing) of",
        ),
        # unreadable collapse of superscript notationinplain  text
        (
            "39188028",
            "reinforcing the growing appreciation of CREBBP<sup>HAT</sup> mutation as a key biological",
            "reinforcing the growing appreciation of CREBBP^HAT mutation as a key biological",
        ),
        (
            "26909576",
            "the TP63∆N transcriptional network",
            "the TP63DeltaN transcriptional network",
        ),
        ("16267625", "3 repeat (TSER(*)3) allele", "3 repeat (TSER(*)3) allele"),
        (
            "32071084",
            "regulatory subunit B'ϵ (PPP2R5ϵ) as a KLHL42 substrate",
            "regulatory subunit B'eps (PPP2R5eps) as a KLHL42 substrate",
        ),
        (
            "32360551",
            r"We performed studies with Ptf1a<sup>Cre</sup>; Kras<sup>G12D</sup>; Setdb1<sup>f/f</sup>, Ptf1a<sup>Cre</sup>; Kras<sup>G12D</sup>; Trp53<sup>f/\+</sup>; Setdb1<sup>f/f</sup>, and Ptf1a<sup>Cre</sup>; Kras<sup>G12D</sup>; Trp53<sup>f/f</sup>; Setdb1<sup>f/f</sup> mice to investigate the effects ",
            "We performed studies with Ptf1a^Cre; Kras^G12D; Setdb1^f/f, Ptf1a^Cre; Kras^G12D; Trp53^f/+; Setdb1^f/f, and Ptf1a^Cre; Kras^G12D; Trp53^f/f; Setdb1^f/f mice to investigate the effects ",
        ),
        # weird punctuation in original article
        ("29394989", "73 had ?95% probability", "73 had ?95% probability"),
        (
            "30820715",
            "response rate of 0%. CTC°3 adverse",
            "response rate of 0%. CTC deg 3 adverse",
        ),
        (
            "33524400",
            "Of the somatic HRDetect<sup>hi</sup> cases",
            "Of the somatic HRDetect^hi cases",
        ),
        (
            "29247009",
            "polymerases (Pol μ and Pol λ), a nuclease",
            "polymerases (Pol mu and Pol lambda), a nuclease",
        ),
        (
            "29756206",
            " gemcitabine (1,000 mg/m<sup>2</sup> ) in 28-day cycles",
            " gemcitabine (1,000 mg/m^2) in 28-day cycles",
        ),
        ("27101865", "α∥ = (3.6 ± 0.2) ", "alpha parallel = (3.6 +/- 0.2) "),
    ],
)
def test_convert_markdown_to_text(pmid, md_content, text_content):
    assert convert_markdown_to_text(md_content).strip() == text_content.strip()


def test_split_articles_from_pubmed_xml():
    from article_converter import split_articles_from_pubmed_xml

    root = etree.Element("PubmedArticleSet")
    for file_id in ("32214442", "34307865"):
        source_root = etree.fromstring(read_test_xml(file_id).encode("utf-8"))
        root.append(source_root[0])
    xml = etree.tostring(root, encoding="unicode")

    result = split_articles_from_pubmed_xml(xml)

    assert set(result) == {"32214442", "34307865"}
    assert "<PubmedArticle" in result["32214442"]
    assert "<PubmedArticle" in result["34307865"]


def test_split_articles_from_pubmed_xml_supports_book_articles():
    from article_converter import split_articles_from_pubmed_xml

    xml = """\
<PubmedArticleSet>
  <PubmedBookArticle>
    <BookDocument>
      <PMID Version="1">31971751</PMID>
      <ArticleTitle>Lung Metastasis</ArticleTitle>
    </BookDocument>
  </PubmedBookArticle>
</PubmedArticleSet>
"""

    result = split_articles_from_pubmed_xml(xml)

    assert set(result) == {"31971751"}
    assert "PubmedBookArticle" in result["31971751"]


def test_split_articles_from_pubmed_xml_requires_pmid():
    from article_converter import split_articles_from_pubmed_xml

    with pytest.raises(ValueError, match="missing a PMID"):
        split_articles_from_pubmed_xml("<PubmedArticleSet><PubmedArticle /></PubmedArticleSet>")


@pytest.mark.parametrize(
    "xml,expected",
    [
        (
            "<article><front><article-meta><abstract><p>Abstract</p></abstract>"
            "</article-meta></front></article>",
            True,
        ),
        (
            "<article><front><article-meta><abstract><p>Abstract</p></abstract>"
            "</article-meta></front><body /></article>",
            True,
        ),
        (
            "<article><front><article-meta><abstract><p>Abstract</p></abstract>"
            "</article-meta></front><body><sec><p>Full text</p></sec></body></article>",
            False,
        ),
    ],
)
def test_is_abstract_only_pmc(xml, expected):
    from article_converter import is_abstract_only

    assert is_abstract_only(xml, source_type="pmc") is expected


def test_is_abstract_only_real_pmc_article():
    from article_converter import is_abstract_only

    assert is_abstract_only(read_test_xml("PMC10139909"), source_type="pmc") is False


def test_is_abstract_only_pubmed():
    from article_converter import is_abstract_only

    assert is_abstract_only(read_test_xml("32214442"), source_type="pubmed") is True
