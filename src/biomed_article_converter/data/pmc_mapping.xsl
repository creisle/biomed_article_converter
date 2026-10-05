<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:mml="http://w3.org"
    exclude-result-prefixes="xlink">


    <xsl:output method="html" encoding="UTF-8" indent="yes" doctype-system="about:legacy-compat" />
    <!-- PMC Root Document Layout -->
    <xsl:template match="article">
        <html>
            <head>
                <meta charset="UTF-8" />
                <title>
                    <xsl:value-of select="front/article-meta/title-group/article-title" />
                </title>
                <!--  Link to an external stylesheet instead of embedding it -->
                <link rel="stylesheet" href="article-styles.css" />
            </head>
            <body>
                <header>
                    <h1>
                        <xsl:value-of select="front/article-meta/title-group/article-title" />
                    </h1>

                    <!-- Authors List structured as an HTML Ordered List -->
                    <ol class="authors-list">
                        <xsl:for-each select="front/article-meta/contrib-group/contrib[@contrib-type='author']">
                            <li class="author-item">
                                <span class="author-name">
                                    <xsl:value-of select="name/given-names"/>
                                    <xsl:text> </xsl:text>
                                    <xsl:value-of select="name/surname"/>

                                    <!-- Loop over every affiliation link this specific author has -->
                                    <xsl:for-each select="xref[@ref-type='aff']">
                                        <sup class="author-aff-link">
                                            <a href="#{@rid}">
                                                <xsl:value-of select="."/>
                                            </a>
                                            <!-- Adds a comma separator if the author has multiple consecutive affiliations -->
                                            <xsl:if test="position() != last()">
                                                <xsl:text>,</xsl:text>
                                            </xsl:if>
                                        </sup>
                                    </xsl:for-each>
                                </span>
                            </li>
                        </xsl:for-each>
                    </ol>

                    <!-- Affiliations structured as an HTML Ordered List -->
                    <ol class="affiliations-list">
                        <xsl:for-each select="front/article-meta//aff">
                            <li class="affiliation-item" id="{@id}">
                                <xsl:apply-templates />
                            </li>
                        </xsl:for-each>
                    </ol>


                    <!-- Extended Publication Metadata Panel -->
                    <section class="metadata-panel">
                        <dl class="metadata-list">
                            <!-- Process and render DOIs and alternative tracking numbers -->
                            <xsl:for-each select="front/article-meta/article-id">
                                <dt>ID (<xsl:value-of select="@pub-id-type"/>):</dt>
                                <dd><xsl:value-of select="."/></dd>
                            </xsl:for-each>

                            <!-- Volume & Issue data -->
                            <xsl:if test="front/article-meta/volume">
                                <dt>Volume:</dt>
                                <dd><xsl:value-of select="front/article-meta/volume"/></dd>
                            </xsl:if>
                            <xsl:if test="front/article-meta/issue">
                                <dt>Issue:</dt>
                                <dd><xsl:value-of select="front/article-meta/issue"/></dd>
                            </xsl:if>

                            <!-- First & Last Page counts -->
                            <xsl:if test="front/article-meta/fpage">
                                <dt>Pages:</dt>
                                <dd><xsl:value-of select="front/article-meta/fpage"/>–<xsl:value-of select="front/article-meta/lpage"/></dd>
                            </xsl:if>

                            <!-- Publication Dates -->
                            <xsl:for-each select="front/article-meta/pub-date">
                                <dt>Published (<xsl:value-of select="@pub-type"/>):</dt>
                                <dd>
                                    <xsl:if test="day"><xsl:value-of select="day"/><xsl:text> </xsl:text></xsl:if>
                                    <xsl:if test="month"><xsl:value-of select="month"/><xsl:text> </xsl:text></xsl:if>
                                    <xsl:value-of select="year"/>
                                </dd>
                            </xsl:for-each>
                        </dl>

                        <!-- Copyright & Licensing Summary Block -->
                        <xsl:if test="front/article-meta/permissions">
                            <div class="article-permissions">
                                <p class="copyright-statement">
                                    <xsl:value-of select="front/article-meta/permissions/copyright-statement"/>
                                </p>
                                <xsl:if test="front/article-meta/permissions/license/license-p">
                                    <p class="license-text">
                                        <xsl:apply-templates select="front/article-meta/permissions/license/license-p"/>
                                    </p>
                                </xsl:if>
                            </div>
                        </xsl:if>
                    </section>
                </header>
                <main>
                    <xsl:apply-templates select="front/article-meta/abstract" />
                    <!-- Render PMC Keywords List -->
                    <xsl:if test="front/article-meta/kwd-group">
                        <section class="keywords-section">
                            <strong>Keywords: </strong>
                            <xsl:for-each select="front/article-meta/kwd-group/kwd">
                                <xsl:apply-templates />
                                <xsl:if test="position() != last()"><xsl:text>, </xsl:text></xsl:if>
                            </xsl:for-each>
                        </section>
                    </xsl:if>
                    <xsl:apply-templates select="body" />
                    <xsl:apply-templates select="back/ref-list" />
                </main>
            </body>
        </html>
    </xsl:template>


    <!-- 2. Reusable Re-routed Authors Block -->
    <xsl:template name="render-authors">
        <xsl:choose>
            <!-- IF PMC XML -->
            <xsl:when test="descendant::contrib[@contrib-type='author']">
                <xsl:for-each select="descendant::contrib[@contrib-type='author']">
                    <span class="author-name">
                        <xsl:value-of select="name/given-names"/>
                        <xsl:text> </xsl:text>
                        <xsl:value-of select="name/surname"/>

                        <!-- PMC Affiliation Links -->
                        <xsl:for-each select="xref[@ref-type='aff']">
                            <sup class="author-aff-link">
                                <a href="#{@rid}"><xsl:value-of select="."/></a>
                                <xsl:if test="position() != last()"><xsl:text>,</xsl:text></xsl:if>
                            </sup>
                        </xsl:for-each>
                    </span>
                    <xsl:if test="position() != last()"><xsl:text>, </xsl:text></xsl:if>
                </xsl:for-each>
            </xsl:when>

            <!-- IF PUBMED XML -->
            <xsl:when test="descendant::Author">
                <xsl:for-each select="descendant::Author">
                    <span class="author-name">
                        <xsl:value-of select="ForeName"/>
                        <xsl:text> </xsl:text>
                        <xsl:value-of select="LastName"/>
                        <xsl:value-of select="CollectiveName"/>

                        <!-- PubMed Dynamic Affiliation Super-scripting -->
                        <xsl:if test="AffiliationInfo/Affiliation">
                            <sup class="author-aff-link">
                                <xsl:variable name="current-aff" select="AffiliationInfo/Affiliation/text()"/>
                                <xsl:value-of select="count(//Affiliation[text() = $current-aff]/preceding::Affiliation[not(text() = preceding::Affiliation/text())]) + 1"/>
                            </sup>
                        </xsl:if>
                    </span>
                    <xsl:if test="position() != last()"><xsl:text>, </xsl:text></xsl:if>
                </xsl:for-each>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <!-- 3. Reusable Re-routed Affiliations Footnote List -->
    <xsl:template name="render-affiliations">
        <xsl:choose>
            <!-- IF PMC XML: Loop through the front text blocks -->
            <xsl:when test="descendant::aff">
                <xsl:for-each select="descendant::aff">
                    <div class="affiliation-item" id="{@id}">
                        <xsl:apply-templates />
                    </div>
                </xsl:for-each>
            </xsl:when>

            <!-- IF PUBMED XML: Extract and unique-filter strings -->
            <xsl:when test="descendant::Affiliation">
                <xsl:for-each select="descendant::Affiliation">
                    <xsl:variable name="current-text" select="text()"/>
                    <xsl:if test="not(preceding::Affiliation[text() = $current-text])">
                        <div class="affiliation-item">
                            <sup class="aff-number">
                                <xsl:value-of select="count(preceding::Affiliation[not(text() = preceding::Affiliation/text())]) + 1"/>
                            </sup>
                            <xsl:value-of select="." />
                        </div>
                    </xsl:if>
                </xsl:for-each>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <!-- Element Templates (These are safe to stay down here) -->
    <xsl:template match="aff">
        <div class="affiliation-item" id="{@id}">
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <xsl:template match="aff/label">
        <sup class="aff-label"><xsl:apply-templates/></sup>
    </xsl:template>

    <!-- Abstract Section -->
    <xsl:template match="abstract">
        <section class="abstract">
            <xsl:apply-templates />
        </section>
    </xsl:template>

    <!-- Top-Level Sections -->
    <xsl:template match="body/sec">
        <section>
            <!-- Map the XML id directly to the HTML id attribute -->
            <xsl:if test="@id">
                <xsl:attribute name="id">
                    <xsl:value-of select="@id"/>
                </xsl:attribute>
            </xsl:if>
            <!-- Retain the sec-type attribute -->
            <xsl:if test="@sec-type">
                <xsl:attribute name="data-sec-type">
                    <xsl:value-of select="@sec-type"/>
                </xsl:attribute>
            </xsl:if>

            <h2>
                <xsl:value-of select="title" />
            </h2>
            <xsl:apply-templates select="*[not(self::title)]" />
        </section>
    </xsl:template>


    <!-- Nested Sub-Sections -->
    <xsl:template match="sec/sec">
        <section class="sub-section">
            <!-- Map the XML id directly to the HTML id attribute -->
            <xsl:if test="@id">
                <xsl:attribute name="id">
                    <xsl:value-of select="@id"/>
                </xsl:attribute>
            </xsl:if>
            <!-- Retain the sec-type attribute -->
            <xsl:if test="@sec-type">
                <xsl:attribute name="data-sec-type">
                    <xsl:value-of select="@sec-type"/>
                </xsl:attribute>
            </xsl:if>

            <h3>
                <xsl:value-of select="title" />
            </h3>
            <xsl:apply-templates select="*[not(self::title)]" />
        </section>
    </xsl:template>


    <!-- Paragraphs & Inline Text Formatting -->
    <xsl:template match="p">
        <p>
            <xsl:apply-templates />
        </p>
    </xsl:template>

    <xsl:template match="bold">
        <strong>
            <xsl:apply-templates />
        </strong>
    </xsl:template>

    <xsl:template match="italic">
        <em>
            <xsl:apply-templates />
        </em>
    </xsl:template>

    <!-- Figures -->
    <xsl:template match="fig">
        <figure id="{@id}" class="article-figure">

            <!-- Extract the graphic filename regardless of namespace variations -->
            <xsl:variable name="raw-href" select="graphic/@*[local-name()='href']"/>

            <!-- Isolate the pure filename (strips out any absolute or relative paths if present) -->
            <xsl:variable name="filename-only">
                <xsl:choose>
                    <xsl:when test="contains($raw-href, '/')">
                        <!-- If the string contains a path, extract everything after the final slash -->
                        <!-- Note: JATS standard strings usually don't have slashes, but this protects it -->
                        <xsl:value-of select="$raw-href"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:value-of select="$raw-href"/>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:variable>

            <!-- Render the image tag using only the standalone file name -->
            <img>
                <xsl:attribute name="src">
                    <xsl:value-of select="$filename-only"/>
                </xsl:attribute>
                <xsl:attribute name="alt">
                    <xsl:value-of select="label"/>
                </xsl:attribute>
            </img>

            <!-- Semantic figure caption -->
            <figcaption>
                <strong class="caption-label"><xsl:value-of select="label"/></strong>
                <xsl:if test="label and caption/p"><xsl:text> </xsl:text></xsl:if>
                <xsl:apply-templates select="caption/p"/>
            </figcaption>
        </figure>
    </xsl:template>

    <!-- Match the alternatives container and only process its table child -->
    <!-- articles sometimes have a fallback graphic for tables -->
    <xsl:template match="alternatives">
        <xsl:apply-templates select="table" />
    </xsl:template>

    <!-- Handle the overall table wrapper container -->
    <xsl:template match="table-wrap">
        <div class="table-wrapper" id="{@id}">
            <!-- Manually render Label & Title up front -->
            <xsl:if test="label">
                <span class="table-label"><strong><xsl:value-of select="label"/>: </strong></span>
            </xsl:if>
            <xsl:if test="caption/title">
                <span class="table-title"><xsl:apply-templates select="caption/title"/></span>
            </xsl:if>

            <!-- CRITICAL FIX: Only jump directly to the table elements. -->
            <!-- This completely bypasses object-id, label, and the duplicate caption blocks -->
            <xsl:apply-templates select="table | alternatives/table"/>

            <!-- Render the extra caption paragraphs below the table if they exist -->
            <xsl:if test="caption/p">
                <div class="table-caption-paragraph">
                    <xsl:apply-templates select="caption/p"/>
                </div>
            </xsl:if>
        </div>
    </xsl:template>

    <!-- Global Structural Table Match (Catches tables anywhere) -->
    <xsl:template match="table">
        <table border="1" class="pmc-table" style="border-collapse: collapse; width: 100%;">
            <xsl:if test="@frame"><xsl:attribute name="data-frame"><xsl:value-of select="@frame"/></xsl:attribute></xsl:if>
            <xsl:if test="@rules"><xsl:attribute name="data-rules"><xsl:value-of select="@rules"/></xsl:attribute></xsl:if>
            <xsl:apply-templates/>
        </table>
    </xsl:template>

    <!--  Handle column groups and individual inline configurations -->
    <xsl:template match="colgroup">
        <colgroup>
            <xsl:apply-templates/>
        </colgroup>
    </xsl:template>

    <xsl:template match="col">
        <col style="text-align: {@align};" />
    </xsl:template>

    <!-- Convert XML <break/> elements to HTML <br> -->
    <xsl:template match="break">
        <br/>
    </xsl:template>

    <!-- Catch-all copies for sub-table components (thead, tbody, tr, td, th) -->
    <xsl:template match="thead | tbody | tr | th | td">
        <xsl:copy>
            <xsl:copy-of select="@*"/>
            <xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>

    <!-- Safeguard: Swallows the fallback preview image so it doesn't break tables -->
    <xsl:template match="graphic | alternatives/graphic" />

    <!-- Cross-References: Maps citations, figures, and table links cleanly -->
    <xsl:template match="xref">
        <a href="#{@rid}" class="article-xref {@ref-type}" data-ref-type="{@ref-type}">
            <xsl:apply-templates/>
        </a>
    </xsl:template>

    <!-- Reference Bibliography List -->
    <xsl:template match="ref-list">
        <footer class="references">
            <h2>References</h2>
            <ol>
                <xsl:apply-templates select="ref" />
            </ol>
        </footer>
    </xsl:template>

    <xsl:template match="ref">
        <li class="ref-item" id="{@id}">
            <xsl:apply-templates select="mixed-citation | element-citation" />
        </li>
    </xsl:template>

    <!-- Emulate PMC Inline Equations -->
    <xsl:template match="inline-formula">
        <span class="inline-formula" xmlns:mml="http://w3.org">
            <xsl:if test="@id">
                <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
            </xsl:if>
            <xsl:choose>
                <!-- If it contains MathML, copy the MathML node block intact -->
                <xsl:when test=".//mml:math">
                    <xsl:copy-of select=".//mml:math" />
                </xsl:when>
                <!-- If it contains TeX, wrap it so MathJax recognizes it -->
                <xsl:when test=".//tex-math">
                    <script type="math/tex"><xsl:value-of select=".//tex-math"/></script>
                </xsl:when>
            </xsl:choose>
        </span>
    </xsl:template>

    <!-- Emulate PMC Display / Block Equations -->
    <xsl:template match="disp-formula">
        <div class="disp-formula" xmlns:mml="http://w3.org">
            <xsl:if test="@id">
                <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
            </xsl:if>
            <xsl:choose>
                <!-- Process MathML block -->
                <xsl:when test=".//mml:math">
                    <xsl:copy-of select=".//mml:math" />
                </xsl:when>
                <!-- Process TeX display block -->
                <xsl:when test=".//tex-math">
                    <script type="math/tex; mode=display"><xsl:value-of select=".//tex-math"/></script>
                </xsl:when>
            </xsl:choose>

            <!-- Retain PMC equation counter labels like (1) -->
            <xsl:if test="label">
                <span class="label"><xsl:value-of select="label"/></span>
            </xsl:if>
        </div>
    </xsl:template>

    <!-- Render text superscripts perfectly intact (e.g. R^2) -->
    <xsl:template match="sup">
        <sup>
            <xsl:if test="@id"><xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute></xsl:if>
            <xsl:apply-templates />
        </sup>
    </xsl:template>

    <!-- Render text subscripts perfectly intact (e.g. R_adj) -->
    <xsl:template match="sub">
        <sub>
            <xsl:if test="@id"><xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute></xsl:if>
            <xsl:apply-templates />
        </sub>
    </xsl:template>

    <!-- Retain italic variables inside paragraph runs (e.g. the letter R) -->
    <xsl:template match="italic | i">
        <em>
            <xsl:apply-templates />
        </em>
    </xsl:template>

    <!-- PMC/JATS external links -->
    <xsl:template match="ext-link[@xlink:href]">
        <a class="ext-link" href="{@xlink:href}">
            <xsl:apply-templates/>
        </a>
    </xsl:template>

    <!-- [<sup> should be normalized to regular text -->
    <xsl:template match="sup[
        preceding-sibling::text()[1][substring(., string-length(.), 1) = '[']
        and
        following-sibling::text()[1][starts-with(., 'H]')]
    ]">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Flatten numeric superscripts used in nucleotide/mutation notation -->
    <xsl:template match="sup[
        number(normalize-space(.)) = number(normalize-space(.))
        and
        (
            preceding-sibling::text()[1][
                contains('ACGT',
                    substring(
                        normalize-space(.),
                        string-length(normalize-space(.)),
                        1
                    )
                )
            ]
            or
            following-sibling::text()[1][
                contains('ACGT', substring(normalize-space(.), 1, 1))
            ]
        )
    ]">
        <xsl:apply-templates/>
    </xsl:template>
</xsl:stylesheet>
