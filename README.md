# DOD-ChatBot

A PDF processing and analysis tool that combines Mistral OCR with Google Gemini for semantic text extraction and understanding, with an interactive chat interface.

## Overview

This project extracts text content from PDF documents using Mistral's OCR service and processes the text into meaningful semantic chunks using Google's Gemini AI. The application consists of a Python backend for PDF processing and a Next.js frontend for user interaction and document chat capabilities.

## Project Structure

- **Backend**: Python-based FastAPI service for PDF processing and AI analysis
- **Frontend**: Next.js web application with TypeScript for user interface
- **Uploads**: Directory for storing uploaded PDF documents

## Features

- PDF document processing with Mistral OCR
- Semantic chunking of text content using Google Gemini
- Extraction of tables and images from PDF documents
- LaTeX formula correction and rendering
- Intelligent organization of document content by sections
- Interactive chat interface for querying document content
- Rate limiting for API requests to prevent quota issues
- Modern web interface for document uploads and result display

## Installation

### Prerequisites

- Python 3.11+ (for backend)
- Node.js 18+ (for frontend)
- Poetry (for Python dependency management)
- npm or yarn (for Node.js dependency management)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install Python dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Create or update the `.env` file with your API keys:
   ```
   MISTRAL_API_KEY='your_mistral_api_key'
   geminiApiKey='your_gemini_api_key'
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

## Usage

### Running the Backend

```bash
cd backend
poetry run python main.py
```

The backend server will start and listen for incoming requests on port 8000.

### Running the Frontend

```bash
cd frontend
npm run dev
# or
yarn dev
```

The frontend development server will start and be available at `http://localhost:3000`.

### Uploading and Processing Documents

1. Navigate to the web interface at `http://localhost:3000`
2. Upload a PDF document using the provided form
3. Wait for processing to complete (status will update automatically)
4. View the processed results including:
   - Extracted and semantically chunked content
   - LaTeX-corrected OCR text with proper formula rendering
   - Document structure analysis

### Chatting with Your Documents

Once a document is processed, you can:

1. Use the chat interface at the bottom of the page
2. Ask questions about the document content
3. Receive AI-generated responses based on the processed document

## Backend Output

The backend processes PDFs and provides:

- Raw OCR results from Mistral with LaTeX formula correction
- Semantically chunked content processed by Gemini, including:
  - Content type (heading, paragraph, list, etc.)
  - Section meaning
  - Text content
  - Summary
  - Page number
- Tables and images extracted from the document

## Technologies Used

- **Backend**:
  - Python with FastAPI for API endpoints
  - [mistralai](https://pypi.org/project/mistralai/) - Mistral AI client for OCR processing and chat
  - [google-genai](https://pypi.org/project/google-genai/) - Google Generative AI client for text analysis
  - Asynchronous background tasks for processing
  - Poetry for dependency management

- **Frontend**:
  - Next.js 15+ with TypeScript and React 19
  - React Markdown with KaTeX for LaTeX formula rendering
  - React Icons for UI elements
  - Tailwind CSS for styling
  - Custom components for file upload, chat interface, and content display

## License

[License Information]

## Contributors

- Keval Shah <keval.arhan@gmail.com>