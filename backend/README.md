# DOD-ChatBot

A PDF processing and analysis tool that combines Mistral OCR with Google Gemini for semantic text extraction and understanding.

## Overview

This project extracts text content from PDF documents using Mistral's OCR service and processes the text into meaningful semantic chunks using Google's Gemini AI. The processed chunks include context, meaning, and summaries that can be used for document understanding or further processing.

## Features

- PDF document processing with Mistral OCR
- Semantic chunking of text content using Google Gemini
- Extraction of tables and images from PDF documents
- Intelligent organization of document content by sections
- Rate limiting for API requests to prevent quota issues

## Installation

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)

### Setup

1. Clone this repository
2. Install dependencies using Poetry:

```bash
poetry install
```

3. Create a `.env` file with your API keys:

```
MISTRAL_API_KEY='your_mistral_api_key'
geminiApiKey='your_gemini_api_key'
```

## Usage

Process a PDF document:

```bash
poetry run python test.py path/to/your/document.pdf
```

If no path is specified, the script will default to processing "Thesis - Saurabh Zinjad.pdf".

## Output

The script outputs:
- Raw OCR results from Mistral
- Semantically chunked content processed by Gemini, including:
  - Content type (heading, paragraph, list, etc.)
  - Section meaning
  - Text content
  - Summary
  - Page number

## Dependencies

- [mistralai](https://pypi.org/project/mistralai/) - Mistral AI client for OCR processing
- [google-genai](https://pypi.org/project/google-genai/) - Google Generative AI client for text analysis

## License

[License Information]

## Contributors

- Keval Shah <keval.arhan@gmail.com>