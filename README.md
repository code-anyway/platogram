# Platogram: Transform Audio into Insightful Essays

Platogram is an open-source project that converts audio content into structured, readable essays with embedded references. It's designed to help researchers, content creators, and knowledge workers extract valuable insights from audio sources like lectures, podcasts, and interviews.

## Key Features

- Convert audio from YouTube, local files, etc into well-structured text.
- Create Paragraphs, summaries, and titles from audio content.
- Maintain references to the original transcript and timestamps.
- Create a searchable knowledge base from processed audio.
- Use the generated content for further AI-powered analysis and content creation.

## Getting Started

### Prerequisites

- Access to Anthropic's Claude API (required)
- Assembly AI API access (optional, for improved transcription)
- Python 3.7+

### Installation

```bash
pip install git+https://github.com/code-anyway/platogram.git
```

## Basic Usage

```python
import platogram as plato


# Initialize models
llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", "YOUR_ANTHROPIC_API_KEY")
asr = plato.asr.get_model("assembly-ai/best", "YOUR_ASSEMBLYAI_API_KEY")  # Optional

  

# Process audio
url = "https://youtu.be/example"
transcript = plato.extract_transcript(url, asr)
content = plato.index(transcript, llm)
  
# Access generated content
print(content.title)
print(content.summary)

for paragraph in content.paragraphs:
    print(paragraph)
```

## Use Cases

- Create searchable archives of lectures or conference talks
- Generate blog posts or articles from podcast episodes
- Extract key insights from interviews or meetings
- Build a personal knowledge base from audio content
- Enhance learning by converting lectures into structured notes
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Uses transcript and text of Chapter 1: Atoms in Motions from Feynman Lectures on Physics, [Copyright © 1963-1965, 2006, 2013 by the California Institute of Technology, Michael A. Gottlieb and Rudolf Pfeiffer](https://www.feynmanlectures.caltech.edu/III_copyright.html)
- Uses Anthropic's Claude for advanced language processing
- Optional integration with Assembly AI for improved transcription

## Feedback and Support

We're actively seeking feedback to improve Platogram. For questions, suggestions, or issues, please contact us at [platogram@codeanyway.com](mailto:platogram@codeanyway.com) or open an issue on GitHub.

Start transforming your audio content into valuable, structured knowledge today with Platogram!
