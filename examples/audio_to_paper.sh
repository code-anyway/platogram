#!/bin/bash

set -e

URL="$1"
LANG="en"
INLINE_REFERENCES="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --lang)
            LANG="$2"
            shift
            shift
            ;;
        --inline-references)
            INLINE_REFERENCES="true"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

case "$LANG" in
  "en")
    CONTRIBUTORS_PROMPT="Thoroughly review the <context> and identify the list of contributors. Output as Markdown list: First Name, Last Name, Title, Organization. Output \"Unknown\" if the contributors are not known. In the end of the list always add \"- [Platogram](https://github.com/code-anyway/platogram), Chief of Stuff, Code Anyway, Inc.\". Start with \"## Contributors, Acknowledgements, Mentions\""
    CONTRIBUTORS_PREFILL=$'## Contributors, Acknowledgements, Mentions\n'

    INTRODUCTION_PROMPT="Thoroughly review the <context> and write \"Introduction\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Introduction\""
    INTRODUCTION_PREFILL=$'## Introduction\n'

    CONCLUSION_PROMPT="Thoroughly review the <context> and write \"Conclusion\" chapter for the paper. Make sure to include <markers>. Output as Markdown. Start with \"## Conclusion\""
    CONCLUSION_PREFILL=$'## Conclusion\n'
    ;;
  "es")
    CONTRIBUTORS_PROMPT="Revise a fondo el <context> e identifique la lista de contribuyentes. Salida como lista Markdown: Nombre, Apellido, Título, Organización. Salida \"Desconocido\" si los contribuyentes no se conocen. Al final de la lista, agregue siempre \"- [Platogram](https://github.com/code-anyway/platogram), Chief of Stuff, Code Anyway, Inc.\". Comience con \"## Contribuyentes, Agradecimientos, Menciones\""
    CONTRIBUTORS_PREFILL=$'## Contribuyentes, Agradecimientos, Menciones\n'

    INTRODUCTION_PROMPT="Revise a fondo el <context> y escriba el capítulo \"Introducción\" para el artículo. Asegúrese de incluir <markers>. Salida como Markdown. Comience con \"## Introducción\""
    INTRODUCTION_PREFILL=$'## Introducción\n'

    CONCLUSION_PROMPT="Revise a fondo el <context> y escriba el capítulo \"Conclusión\" para el artículo. Asegúrese de incluir <markers>. Salida como Markdown. Comience con \"## Conclusión\""
    CONCLUSION_PREFILL=$'## Conclusión\n'
    ;;
  *)
    echo "Unsupported language: $LANG"
    exit 1
    ;;
esac

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
        plato --images "$URL" --lang "$LANG" > /dev/null
    else
        plato "$URL" --lang "$LANG" > /dev/null
    fi
else
    echo "Transcribing audio to text using AssemblyAI..."

    if [ "$2" = "--images" ]; then
        plato --images "$URL" --assemblyai-api-key $ASSEMBLYAI_API_KEY --lang "$LANG" > /dev/null
    else
        plato "$URL" --assemblyai-api-key $ASSEMBLYAI_API_KEY --lang "$LANG" > /dev/null
    fi
fi

echo "Fetching title, abstract, passages, and references..."
TITLE=$(plato --title "$URL" --lang "$LANG")
ABSTRACT=$(plato --abstract "$URL" --lang "$LANG")
PASSAGES=$(plato --passages --chapters --inline-references "$URL" --lang "$LANG")
REFERENCES=$(plato --references "$URL" --lang "$LANG")
CHAPTERS=$(plato --chapters "$URL" --lang "$LANG")

echo "Generating Contributors..."
CONTRIBUTORS=$(plato \
    --query "$CONTRIBUTORS_PROMPT" \
    --generate \
    --context-size large \
    --inline-references \
    --prefill "$CONTRIBUTORS_PREFILL" \
    "$URL" --lang "$LANG")

echo "Generating Introduction..."
INTRODUCTION=$(plato \
    --query "$INTRODUCTION_PROMPT" \
    --generate \
    --context-size large \
    --inline-references \
    --prefill "$INTRODUCTION_PREFILL" \
    "$URL" --lang "$LANG")

echo "Generating Conclusion..."
CONCLUSION=$(plato \
    --query "$CONCLUSION_PROMPT" \
    --generate \
    --context-size large \
    --inline-references \
    --prefill "$CONCLUSION_PREFILL" \
    "$URL" --lang "$LANG")

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
    echo $'## References\n\n'"$REFERENCES"$'\n'
) | \
    if [ "$INLINE_REFERENCES" = "true" ]; then
        cat
    else
        sed -E 's/\[\[([0-9]+)\]\]\([^)]+\)//g' | \
        sed -E 's/\[([0-9]+)\]//g'
    fi | \
    tee \
    >(pandoc -o "$(echo "$TITLE" | sed 's/[^a-zA-Z0-9]/_/g').docx" --from markdown) \
    >(pandoc -o "$(echo "$TITLE" | sed 's/[^a-zA-Z0-9]/_/g').pdf" --from markdown --pdf-engine=xelatex) \
    >(pandoc -o "$(echo "$TITLE" | sed 's/[^a-zA-Z0-9]/_/g').md" --from markdown) > /dev/null
wait