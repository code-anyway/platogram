# Audio to Paper Conversion Script

This script converts audio content into a structured paper format using Platogram.

## Prerequisites

- Bash environment
- [Platogram](https://github.com/code-anyway/platogram) installed
- ANTHROPIC_API_KEY (required)
- ASSEMBLYAI_API_KEY (optional, for audio transcription)

## Usage

```bash
./audio_to_paper.sh <URL> [--images]
```

- `<URL>`: The URL of the audio content
- `--images` (optional): Include images

## Features

1. Transcribes audio to text (if `ASSEMBLYAI_API_KEY` is set) or uses subtitles, srt, vtt.
2. Generates paper components:
   - Title
   - Abstract
   - Contributors
   - Chapters
   - Introduction
   - Discussion with chapters
   - Conclusion
   - References
3. Outputs the paper in multiple formats:
   - Markdown (.md)
   - Microsoft Word (.docx)
   - PDF (.pdf)

## Output

The script generates three files with the paper's title as the filename (special characters replaced with underscores):

1. `<title>.md`
2. `<title>.docx`
3. `<title>.pdf`

## Notes

- Ensure ANTHROPIC_API_KEY is set in your environment
- For audio transcription, set ASSEMBLYAI_API_KEY in your environment
- Without ASSEMBLYAI_API_KEY, the script will attempt to retrieve text from the URL (e.g., subtitles)
