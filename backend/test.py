import sys
import json
import os
import re
import time
import uvicorn
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware  # Add this import
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from mistralai import DocumentURLChunk, Mistral
from google import genai

app = FastAPI(title="PDF OCR & Analysis API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend's URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Keep all the existing functions
def extract_json_from_gemini_response(response_text):
    """
    Extract JSON content from a Gemini response string that may be wrapped
    in code fence markers (e.g., ```json ... ```). Also fixes invalid escape sequences.
    
    Args:
        response_text (str): The full text response from Gemini.
    
    Returns:
        dict: The parsed JSON object.
    
    Raises:
        ValueError: If no valid JSON content can be extracted.
    """
    # Look for JSON content between code fence markers
    pattern = r"```json\s*(\{.*\})\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # If not wrapped in code fences, assume the response is pure JSON
        json_str = response_text

    # The issue is likely with escape sequences in the response
    # Approach 1: Replace all backslashes with double backslashes
    json_str = json_str.replace("\\", "\\\\")
    
    # But we need to fix double-escaped quotes, which should remain as \"
    json_str = json_str.replace("\\\\\"", "\\\"")
    
    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError as e:
        # If the first approach fails, try a more targeted approach
        try:
            # Original string with more specific escape sequence handling
            json_str = match.group(1) if match else response_text
            # Replace only invalid escape sequences
            json_str = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', json_str)
            data = json.loads(json_str)
            return data
        except Exception as nested_e:
            raise ValueError(f"Error decoding JSON from Gemini response: {e}. Additional error: {nested_e}")

def process_pdf_with_ocr(pdf_path, api_key=None):
    """
    Process a PDF file with Mistral's OCR service.
    
    Args:
        pdf_path (str): Path to the PDF file.
        api_key (str, optional): Mistral API key. If None, it will be taken from the environment variable.
        
    Returns:
        dict: The OCR processing results.
    """
    if api_key is None:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found in environment variables")
    
    client = Mistral(api_key=api_key)
    
    pdf_file = Path(pdf_path)
    if not pdf_file.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    uploaded_file = client.files.upload(
        file={
            "file_name": pdf_file.stem,
            "content": pdf_file.read_bytes(),
        },
        purpose="ocr",
    )
    
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
    
    pdf_response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest",
        include_image_base64=True
    )
    
    return json.loads(pdf_response.model_dump_json())

def process_ocr_results_for_embedding(ocr_result):
    """
    Process OCR results into meaningful semantic chunks using Google Gemini.
    
    Args:
        ocr_result (dict): The OCR processing results from Mistral OCR.
        
    Returns:
        list: List of semantic chunks (each chunk is a dictionary).
    """
    gemini_api_key = os.environ.get("geminiApiKey")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    gemini_client = genai.Client(api_key=gemini_api_key)
    model = 'gemini-2.0-flash'
    
    # Rate limiting: track the number of requests and the start time of the window
    gemini_request_count = 0
    gemini_request_start = time.time()
    
    chunks = []
    
    if "pages" in ocr_result:
        for page_idx, page in enumerate(ocr_result["pages"]):
            page_number = page_idx + 1
            # Use "text" if available; otherwise, fallback to "markdown"
            page_content = page.get("text") or page.get("markdown")
            
            if page_content and page_content.strip():
                # Rate limit: If 15 requests have been sent, check the time elapsed
                if gemini_request_count >= 15:
                    elapsed = time.time() - gemini_request_start
                    if elapsed < 60:
                        sleep_time = 60 - elapsed
                        print(f"Reached 15 Gemini requests in this minute. Sleeping for {sleep_time:.2f} seconds.")
                        time.sleep(sleep_time)
                    # Reset the counter and window
                    gemini_request_count = 0
                    gemini_request_start = time.time()
                
                prompt = (
                    "Analyze the following page content and divide it into distinct sections. "
                    "Treat each section as a logically self-contained unit of information—this could be a header with its related text, a group of paragraphs, a list, etc. "
                    "For each section, provide the following keys:\n"
                    "  - 'content': The full text content of the section.\n"
                    "  - 'type': The type or category of the section (for example, heading, paragraph, list, etc.).\n"
                    "  - 'meaning': A description of what the section represents (e.g., 'Education details', 'Work experience', 'Project summary', etc.).\n"
                    "  - 'summary': A brief summary highlighting the key points of the section.\n"
                    "Return a JSON object with a key 'chunks' mapping to an array of these objects, ensuring each distinct section is returned as a separate chunk.\n\n"
                    f"Page content: {page_content}"
                )
                
                try:
                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=prompt,
                    )
                    gemini_request_count += 1  # Increment the request counter
                    print(f"Gemini response for page {page_number}: {response.text}")
                    
                    # Extract and fix JSON from the Gemini response
                    llm_chunks_data = extract_json_from_gemini_response(response.text)
                    
                    # Attach the page number to each chunk
                    for chunk in llm_chunks_data.get("chunks", []):
                        chunk["page"] = page_number
                        chunks.append(chunk)
                except Exception as e:
                    print(f"Error processing page {page_number} with Gemini: {e}")
                    # Fallback: add the full page content as one chunk with basic information
                    chunks.append({
                        "type": "text",
                        "page": page_number,
                        "content": page_content,
                        "meaning": "Full page text without further chunking.",
                        "summary": "Fallback chunk."
                    })
            
            # Process tables if they exist on the page
            if "tables" in page and page["tables"]:
                for table_idx, table in enumerate(page["tables"]):
                    chunks.append({
                        "type": "table",
                        "page": page_number,
                        "table_index": table_idx,
                        "content": table,
                        "meaning": "Table data extracted from the page.",
                        "summary": "Table representation."
                    })
            
            # Process images if they exist on the page
            if "images" in page and page["images"]:
                for img_idx, img in enumerate(page["images"]):
                    img_data = {
                        "type": "image",
                        "page": page_number,
                        "image_index": img_idx,
                        "meaning": "Visual content on the page.",
                        "summary": "Extracted image."
                    }
                    if "caption" in img:
                        img_data["caption"] = img["caption"]
                    if "base64" in img:
                        img_data["image_data"] = img["base64"]
                    chunks.append(img_data)
    
    return chunks

# Define Pydantic models for request/response
class ProcessResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    
# Store for background jobs
jobs = {}

# Process PDF in background
async def process_pdf_task(job_id: str, file_path: str):
    try:
        jobs[job_id]["status"] = "processing_ocr"
        ocr_results = process_pdf_with_ocr(file_path)
        
        jobs[job_id]["status"] = "processing_chunks"
        chunks = process_ocr_results_for_embedding(ocr_results)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "ocr_results": ocr_results,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# API endpoints
@app.get("/")
async def root():
    return {"message": "PDF OCR & Analysis API is running"}

@app.post("/process", response_model=ProcessResponse)
async def process_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        # Save uploaded file
        file_path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # Create a job ID
        job_id = f"job_{int(time.time())}_{hash(file.filename) % 10000}"
        jobs[job_id] = {"status": "queued"}
        
        # Process in background
        background_tasks.add_task(process_pdf_task, job_id, file_path)
        
        return ProcessResponse(
            job_id=job_id,
            status="queued",
            message="PDF processing has been queued."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = jobs[job_id]["status"]
    response = JobStatusResponse(job_id=job_id, status=status)
    
    if status == "completed":
        response.result = jobs[job_id]["result"]
    elif status == "failed":
        response.result = {"error": jobs[job_id].get("error", "Unknown error")}
    
    return response

if __name__ == "__main__":
    uvicorn.run("test:app", host="0.0.0.0", port=8000, reload=True)
