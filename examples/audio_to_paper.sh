#/bin/bash

URL=$1
plato \
    --assemblyai-api-key $ASSEMBLYAI_API_KEY \
    $URL
plato \
    --prompt "Thoroughly review the <context> and write \"Introduction\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Introduction\"" \
    --context-size medium \
    --inline-references \
    $URL > introduction.md
plato \
    --prompt "Thoroughly review the <context> and write \"Conclusion\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Conclusion\"" \
    --context-size medium \
    --inline-references \
    $URL > conclusion.md
plato \
    --prompt "Thoroughly review the <context> and identify the list of authors. Output as Markdown list: First Name, Last Name, Title, Organization. Start with \"## Authors\"" \
    --context-size medium \
    --inline-references \
    $URL > authors.md
plato \
    --title \
    $URL > title.md
plato \
    --abstract \
    $URL > abstract.md
plato \
    --discussion \
    --inline-references \
    $URL > discussion.md
plato \
    --references \
    $URL > references.md

pandoc \
    title.md \
    authors.md \
    abstract.md \
    introduction.md \
    discussion.md \
    conclusion.md \
    references.md \
    -o output.pdf --from markdown
