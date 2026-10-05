<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    exclude-result-prefixes="#default">

    <xsl:output method="html" encoding="UTF-8" indent="yes" doctype-system="about:legacy-compat" />

    <!-- Index all affiliation text node values to allow grouping and numbering -->
    <xsl:key name="aff-group" match="Affiliation" use="text()" />

    <!-- Absolute Root Entry -->
    <xsl:template match="/">
        <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <title>
                    <xsl:value-of select="PubmedArticleSet/PubmedArticle[1]/MedlineCitation/Article/ArticleTitle" />
                </title>
                <link rel="stylesheet" href="article-styles.css" />
            </head>
            <body>
                <xsl:apply-templates select="PubmedArticleSet/PubmedArticle | PubmedArticle" />
            </body>
        </html>
    </xsl:template>

    <!-- PubMed Article Layout Structure -->
    <xsl:template match="PubmedArticle">
        <header>
            <h1><xsl:value-of select="MedlineCitation/Article/ArticleTitle" /></h1>

            <!-- Authors List structured as an HTML Ordered List -->
            <ol class="authors-list">
                <xsl:for-each select="MedlineCitation/Article/AuthorList/Author">
                    <li class="author-item">
                        <span class="author-name">
                            <xsl:value-of select="ForeName"/>
                            <xsl:text> </xsl:text>
                            <xsl:value-of select="LastName"/>
                            <xsl:value-of select="CollectiveName"/>

                            <!-- Internal link to the unique affiliation footnote index -->
                            <xsl:if test="AffiliationInfo/Affiliation">
                                <xsl:variable name="author-aff-text" select="AffiliationInfo/Affiliation/text()"/>
                                <sup class="author-aff-link">
                                    <a href="#aff-{generate-id(key('aff-group', $author-aff-text))}">
                                        <xsl:value-of select="count(key('aff-group', $author-aff-text)/preceding::Affiliation[generate-id(.) = generate-id(key('aff-group', text()))]) + 1"/>
                                    </a>
                                </sup>
                            </xsl:if>
                        </span>
                    </li>
                </xsl:for-each>
            </ol>

            <!-- Footnote Unique Affiliations Block structured as an HTML Ordered List -->
            <ol class="affiliations-list">
                <xsl:for-each select="MedlineCitation/Article/AuthorList/Author/AffiliationInfo/Affiliation">
                    <xsl:variable name="current-text" select="text()"/>

                    <!-- Only print out the item if it is the first occurrence of this exact text string -->
                    <xsl:if test="generate-id(.) = generate-id(key('aff-group', $current-text))">
                        <li class="affiliation-item" id="aff-{generate-id(.)}">
                            <xsl:value-of select="." />
                        </li>
                    </xsl:if>
                </xsl:for-each>
            </ol>

            <!-- Publication Metadata Panel -->
            <section class="metadata-panel">
                <dl class="metadata-list">
                    <dt>Journal:</dt>
                    <dd><em><xsl:value-of select="MedlineCitation/Article/Journal/Title" /></em></dd>

                    <dt>ID (pmid):</dt>
                    <dd><xsl:value-of select="MedlineCitation/PMID" /></dd>

                    <xsl:if test="PubmedData/ArticleIdList/ArticleId[@IdType='doi']">
                        <dt>ID (doi):</dt>
                        <dd><xsl:value-of select="PubmedData/ArticleIdList/ArticleId[@IdType='doi']" /></dd>
                    </xsl:if>

                    <xsl:if test="MedlineCitation/Article/Journal/JournalIssue/Volume">
                        <dt>Volume:</dt>
                        <dd><xsl:value-of select="MedlineCitation/Article/Journal/JournalIssue/Volume"/></dd>
                    </xsl:if>

                    <xsl:if test="MedlineCitation/Article/Journal/JournalIssue/Issue">
                        <dt>Issue:</dt>
                        <dd><xsl:value-of select="MedlineCitation/Article/Journal/JournalIssue/PubDate/Year"/></dd>
                    </xsl:if>

                    <dt>Published:</dt>
                    <dd><xsl:value-of select="MedlineCitation/Article/Journal/JournalIssue/PubDate/Year"/></dd>
                </dl>
            </section>
        </header>

        <main>
            <!-- Render Abstract Text Segment -->
            <xsl:if test="MedlineCitation/Article/Abstract">
                <section class="abstract-section">
                    <xsl:apply-templates select="MedlineCitation/Article/Abstract/AbstractText" />
                </section>
            </xsl:if>

            <!-- Render Keywords List -->
            <xsl:if test="MedlineCitation/KeywordList">
                <section class="keywords-section">
                    <strong>Keywords: </strong>
                    <xsl:for-each select="MedlineCitation/KeywordList/Keyword">
                        <xsl:value-of select="."/>
                        <xsl:if test="position() != last()"><xsl:text>, </xsl:text></xsl:if>
                    </xsl:for-each>
                </section>
            </xsl:if>
        </main>
    </xsl:template>

    <!-- Dynamic Inline and Block Text Formatting Rules (CLEANED UP TO AVOID DUPLICATES) -->
    <xsl:template match="AbstractText">
        <p>
            <xsl:if test="@Label"><strong><xsl:value-of select="@Label"/>: </strong></xsl:if>
            <xsl:apply-templates />
        </p>
    </xsl:template>

    <!-- Inline elements map tightly on a single line to guarantee zero leaked space strings -->
    <xsl:template match="sup"><sup><xsl:apply-templates/></sup></xsl:template>
    <xsl:template match="sub"><sub><xsl:apply-templates/></sub></xsl:template>
    <xsl:template match="bold | b"><strong><xsl:apply-templates/></strong></xsl:template>
    <xsl:template match="italic | i"><em><xsl:apply-templates/></em></xsl:template>
</xsl:stylesheet>
