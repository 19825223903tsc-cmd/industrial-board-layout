# English board typography

Read this file for every composition. The primary board copy is English even when the conversation is Chinese. Preserve supplied brand and model names; do not introduce Chinese translations. For a Chinese board, use the independent industrial-board-layout-zh skill and recompose using real Chinese copy.

## Hierarchy and text color

- Choose an available Latin font and measure the actual headings, prose and captions. Never estimate English capacity from a CJK character grid. Record font, size, leading and case for each role.
- Set a consistent heading case convention for this project, such as sentence case or title case, while preserving official brand/model capitalization. All caps may suit short labels; long uppercase prose needs its own readability review.
- Size headings by hierarchy and reading conditions. A longer English title does not inherit the Chinese box, size or line count. Widen or reposition its area when needed; do not horizontally stretch letters or shrink everything to fit.
- Use a ragged right edge for normal body copy unless the actual rendering environment and project support carefully reviewed justification. Do not use tracking to force text to full column width.
- Keep numbers, headings and subheadings as separate positioned elements. Check the first baseline and actual glyph bounds; identical top coordinates do not establish optical alignment across font roles.

## Word wrapping and captions

- Wrap at word boundaries. Protect brand/model names, meaningful number-unit pairs and semantic phrases where appropriate. Do not insert hard line breaks copied from a Chinese version.
- A long technical word or model ID that does not fit is an explicit layout problem: widen the text area, move the module or propose an approved shorter label. Never silently split identifiers, change spelling, or clip the word.
- Review single-word last lines, isolated short words, awkward heading breaks and paragraph orphans. A script warning identifies a candidate, not automatic rejection of an intentionally short caption.
- Hyphenation requires an appropriate language-aware mechanism and visual inspection. The bundled renderer does not implement a professional hyphenation engine; never describe a character split as correct hyphenation.
- Measure each real caption. Coordinate the first baseline, image-caption gap and intended final baseline across the row. Different text lengths may require different widths or edited draft copy; do not pad with repeated words or empty lines to fake alignment.

## Spatial composition and handoff

Recalculate column width, line count, text height and adjacent image positions from the English copy. Keep product-driven hierarchy and source identity; English and Chinese outputs need not share every coordinate. Reuse the project's thin image gutters and distinct group/caption spacing where they express the same relationship.

Set canvas.language=en; declare the font and language for each heading/body/caption role. The CLI fills missing language and a suitable available Latin font. It rejects a Chinese-primary layout instead of silently making a bilingual board. A genuinely required non-English proper name/quotation needs an explicit language_exception_note and a font supporting its glyphs; do not use that exception for ordinary Chinese prose.

The image-model prompt must specify English copy, the chosen heading case, word-based wrapping, separate number/title anchors, caption association and shared baselines. Remove placeholder labels and guide lines. Do not promise exact spelling or pixel-perfect coordinates in generated output: inspect the model's actual text separately.
