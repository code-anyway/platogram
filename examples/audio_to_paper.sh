#!/bin/bash

set -e

URL="$1"

# check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ANTHROPIC_API_KEY is not set"
    echo "Obtain it from https://console.anthropic.com/keys"
    echo "Run: export ANTHROPIC_API_KEY=<your-api-key>"
    exit 1
fi

echo "Indexing $URL..."
if [ -z "$ASSEMBLYAI_API_KEY" ]; then
    echo "ASSEMBLYAI_API_KEY is not set. Retrieving text from URL (subtitles, etc)."

    if [ "$2" = "--images" ]; then
        plato --images "$URL" > /dev/null
    else
        plato "$URL" > /dev/null
    fi
else
    echo "Transcribing audio to text using AssemblyAI..."

    if [ "$2" = "--images" ]; then
        plato --images "$URL" --assemblyai-api-key $ASSEMBLYAI_API_KEY > /dev/null
    else
        plato "$URL" --assemblyai-api-key $ASSEMBLYAI_API_KEY > /dev/null
    fi
fi

echo "Fetching title, abstract, passages, and references..."
TITLE=$(plato --title "$URL")
ABSTRACT=$(plato --abstract "$URL")
PASSAGES=$(plato --passages --chapters "$URL")
REFERENCES=$(plato --references "$URL")
CHAPTERS=$(plato --chapters "$URL")

echo "Generating Contributors..."
CONTRIBUTORS=$(plato \
    --query "Thoroughly review the <context> and identify the list of contributors. Output as Markdown list: First Name, Last Name, Title, Organization. Output \"Unknown\" if the contributors are not known. In the end of the list always add \"- [Platogram](https://github.com/code-anyway/platogram), Chief of Stuff, Code Anyway, Inc.\". Start with \"## Contributors, Acknowledgements, Mentions\"" \
    --generate \
    --context-size large \
    --inline-references \
    --prefill $'## Contributors Acknowledgements, Mentions\n' \
    "$URL")

echo "Generating Introduction..."
INTRODUCTION=$(plato \
    --query "Thoroughly review the <context> and write \"Introduction\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Introduction\"" \
    --generate \
    --context-size large \
    --inline-references \
    --prefill $'## Introduction\n' \
    "$URL")

echo "Generating Conclusion..."
CONCLUSION=$(plato \
    --query "Thoroughly review the <context> and write \"Conclusion\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Conclusion\"" \
    --generate \
    --context-size large \
    --inline-references \
    --prefill $'## Conclusion\n' \
    "$URL")

echo "Generating Documents..."
(
    echo $'# '"$TITLE"$'\n'
    echo $'## Origin\n\n'"$URL"$'\n'
    echo $'## Abstract\n\n'"$ABSTRACT"$'\n'
    echo "$CONTRIBUTORS"$'\n'
    echo $'## Chapters\n\n'"$CHAPTERS"$'\n'
    echo "$INTRODUCTION"$'\n'
    echo $'## Discussion\n\n'"$PASSAGES"$'\n'
    echo "$CONCLUSION"$'\n'
#    echo $'## References\n\n'"$REFERENCES"$'\n'
) | sed -E 's/\[\[([0-9]+)\]\]\([^)]+\)/ /g' | sed -E 's/\[([0-9]+)\]/ /g' | tee >(pandoc -o "$(echo "$TITLE" | sed 's/[^a-zA-Z0-9]/_/g').docx" --from markdown) \
                                                                           >(pandoc -o "$(echo "$TITLE" | sed 's/[^a-zA-Z0-9]/_/g').pdf" --from markdown --pdf-engine=xelatex) \
                                                                           >(pandoc -o "$(echo "$TITLE" | sed 's/[^a-zA-Z0-9]/_/g').md" --from markdown) > /dev/null
