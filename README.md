# Platogram: Transform Audio into Knowledge

Platogram is an open-source project that converts audio content into structured, readable essays with embedded references. It's designed to help researchers, content creators, and knowledge workers extract valuable insights from audio sources like lectures, podcasts, and interviews.

## Key Features

- Convert audio from YouTube, local files, etc into well-structured text.
- Create passages, summaries, and titles from audio content.
- Maintain references to the original transcript and timestamps.
- Create a searchable knowledge base from processed audio.
- Use the generated content for further AI-powered analysis and content creation.

## Getting Started

<a target="_blank" href="https://colab.research.google.com/github/code-anyway/platogram/blob/main/notebooks/quick_start.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

### Prerequisites

- Access to Anthropic's Claude API (required)
- Python 3.10+
- FFmpeg (for audio/video conversion)
- whisper.cpp (installed via `brew install whisper-cpp`)
- Assembly AI API access (optional, alternative to local Whisper)

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install platogram
uv pip install git+https://github.com/code-anyway/platogram.git
```

## Basic Usage

### Command Line Interface (CLI)

Obtain your API key for Anthropic. Local Whisper transcription is used by default.

```bash
plato \
--anthropic-api-key "YOUR_ANTHROPIC_API_KEY" \
https://www.youtube.com/shorts/XsLK3tPy9SI
```

You can specify the Whisper model size for better accuracy vs speed tradeoff:

```bash
plato \
--anthropic-api-key "YOUR_ANTHROPIC_API_KEY" \
--whisper-model large-v3 \
https://www.youtube.com/shorts/XsLK3tPy9SI
```

Or use AssemblyAI if you prefer:

```bash
plato \
--anthropic-api-key "YOUR_ANTHROPIC_API_KEY" \
--assemblyai-api-key "YOUR_ASSEMBLYAI_API_KEY" \
https://www.youtube.com/shorts/XsLK3tPy9SI
```

### Python SDK

```python
import platogram as plato


# Initialize models
llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", "YOUR_ANTHROPIC_API_KEY")
asr = plato.asr.get_model("whisper-local/large-v3")  # Local Whisper (default)
# asr = plato.asr.get_model("assembly-ai/best", "YOUR_ASSEMBLYAI_API_KEY")  # Alternative

# Process audio
url = "https://www.youtube.com/shorts/XsLK3tPy9SI"
transcript = plato.extract_transcript(url, asr)
content = plato.index(transcript, llm)
  
# Access generated content
print(content.title)
print(content.summary)

for passage in content.passages:
    print(passage)
```

## Use Cases

- Create searchable archives of lectures or conference talks
- Generate blog posts or articles from podcast episodes
- Extract key insights from interviews or meetings
- Build a personal knowledge base from audio content
- Enhance learning by converting lectures into structured notes

## Acknowledgments

- Uses transcript and text of Chapter 1: Atoms in Motions from Feynman Lectures on Physics, [Copyright © 1963-1965, 2006, 2013 by the California Institute of Technology, Michael A. Gottlieb and Rudolf Pfeiffer](https://www.feynmanlectures.caltech.edu/III_copyright.html)

## Feedback and Support

We're actively seeking feedback to improve Platogram. For questions, suggestions, or issues, please contact us at [platogram@codeanyway.com](mailto:platogram@codeanyway.com) or open an issue on GitHub.

Start transforming your audio content into valuable, structured knowledge today with Platogram!

## Copyright and License

Copyright (c) 2023-2024 Code Anyway, Inc.
https://codeanyway.com

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
