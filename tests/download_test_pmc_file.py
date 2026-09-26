"""
Helper script to download PMC/PubMed files to include in tests/data
"""

import argparse
import logging
import os

import requests


def fetch_xml(pmc_id: str, db_name="pmc") -> str:
    """
    https://www.ncbi.nlm.nih.gov/pmc/tools/get-full-text/
    """
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    resp = requests.get(efetch_url, params={"db": db_name, "id": pmc_id, "rettype": "xml"})
    resp.raise_for_status()
    return resp.text


logger = logging.getLogger("article_fetch")

parser = argparse.ArgumentParser()

parser.add_argument("pmcid", help="ex. PMC6547681")
args = parser.parse_args()


if not os.path.exists(f"tests/data/{args.pmcid}.xml"):
    content = fetch_xml(args.pmcid, "pmc" if args.pmcid.startswith("PMC") else "pubmed")

    print(f"writing: tests/data/{args.pmcid}.xml")
    with open(f"tests/data/{args.pmcid}.xml", "w") as fh:
        fh.write(content)
