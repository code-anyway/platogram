#!/bin/bash

URL="$1"

# check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ANTHROPIC_API_KEY is not set"
    echo "Obtain it from https://console.anthropic.com/keys"
    echo "Run: export ANTHROPIC_API_KEY=<your-api-key>"
    exit 1
fi

# check is ASSEMBLYAI_API_KEY is set
if [ -z "$ASSEMBLYAI_API_KEY" ]; then
    # Retrieve text from URL (subtitles, etc)
    plato \
        "$URL"
else
    # Transcribe audio to text
    plato \
        --assemblyai-api-key $ASSEMBLYAI_API_KEY \
        "$URL"
fi

echo "Generating Documents..."

(
    echo -n $'\n# '
    plato \
        --title \
        "$URL"
    echo $'## Origin\n'
    plato \
        --origin \
        "$URL"
    plato \
        --query "Thoroughly review the <context> and identify the list of contributors. Output as Markdown list: First Name, Last Name, Title, Organization. Output \"Unknown\" if the contributors are not known. In the end of the list always add \"- [Platogram](https://github.com/code-anyway/platogram), Chief of Stuff, Code Anyway, Inc.\". Start with \"## Contributors\"" \
        --generate \
        --context-size large \
        --inline-references \
        --prefill $'## Contributors\n' \
        "$URL"
    echo $'## Abstract\n'
    plato \
        --abstract \
        "$URL"
    plato \
        --query "Thoroughly review the <context> and write \"Introduction\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Introduction\"" \
        --generate \
        --context-size large \
        --inline-references \
        --prefill $'## Introduction\n' \
        "$URL"
    echo $'## Discussion\n'
    plato \
        --passages \
        --inline-references \
        "$URL"
    plato \
        --query "Thoroughly review the <context> and write \"Conclusion\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Conclusion\"" \
        --generate \
        --context-size large \
        --inline-references \
        --prefill $'## Conclusion\n' \
        "$URL"
    echo $'## References\n'
    plato \
        --references \
        "$URL"
) | pandoc \
    -o "$(echo "$URL" | sed 's/[^a-zA-Z0-9]/_/g').docx" --from markdown \
    -o "$(echo "$URL" | sed 's/[^a-zA-Z0-9]/_/g').pdf" --from markdown
