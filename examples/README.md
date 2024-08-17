# Audio to Paper Converter

This Bash script converts audio content or web pages into structured academic papers in PDF format.

## Features

- Supports English and Spanish languages
- Generates papers with and without references
- Can process audio files (using AssemblyAI) or web pages
- Generates title, abstract, contributors, introduction, discussion, and conclusion sections
- Outputs PDFs using Pandoc and LaTeX

## Prerequisites

- Bash environment
- Pandoc and XeLaTeX installed
- `plato` command-line tool (assumed to be a custom tool for content processing)
- ANTHROPIC_API_KEY set in environment variables
- (Optional) ASSEMBLYAI_API_KEY for audio transcription

## Usage
   
```bash
./audio_to_paper.sh <URL> [--lang <language>] [--verbose] [--images]
```

- `<URL>`: The URL of the audio file or web page to process
- `--lang`: Specify language (en or es, default: en)
- `--verbose`: Enable verbose output
- `--images`: Include image processing (if supported by plato)

## Output

The script generates two PDF files:
1. `<title>-no-refs.pdf`: Paper without references
2. `<title>-refs.pdf`: Paper with references

## Note

Ensure all required API keys are set and dependencies are installed before running the script.