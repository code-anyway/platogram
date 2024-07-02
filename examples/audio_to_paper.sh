#!/bin/bash

URL=$1

plato \
    --assemblyai-api-key $ASSEMBLYAI_API_KEY \
    $URL

echo "Generating PDF..."

(
    echo -n $'\n# '
    plato \
        --title \
        $URL
    plato \
        --prompt "Thoroughly review the <context> and identify the list of contributors. Output as Markdown list: First Name, Last Name, Title, Organization. Output \"Unknown\" if the contributors are not known. Start with \"## Contributors\"" \
        --context-size medium \
        --inline-references \
        --prefill $'## Contributors\n' \
        $URL
    echo $'## Abstract\n'
    plato \
        --abstract \
        $URL
    plato \
        --prompt "Thoroughly review the <context> and write \"Introduction\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Introduction\"" \
        --context-size medium \
        --inline-references \
        --prefill $'## Introduction\n' \
        $URL
    plato \
        --passages \
        --inline-references \
        $URL
    plato \
        --prompt "Thoroughly review the <context> and write \"Conclusion\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Conclusion\"" \
        --context-size medium \
        --inline-references \
        --prefill $'## Conclusion\n' \
        $URL
    echo $'## References\n'
    plato \
        --references \
        $URL
) | pandoc \
    -o "$(echo "$URL" | sed 's/[^a-zA-Z0-9]/_/g').pdf" --from markdown
