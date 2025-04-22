import sys
import json
import os
import re
import time
import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from mistralai import DocumentURLChunk, Mistral
from google import genai

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("pdf-api")

app = FastAPI(title="PDF OCR & Analysis API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust to your frontend URL if different
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_json_from_gemini_response(response_text):
    """
    Extract JSON content from a Gemini response string that may be wrapped
    in code fence markers (e.g., ```json ... ```). Also fixes invalid escape sequences.
    """
    try:
        pattern = r"```json\s*(\{.*\})\s*```"
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            json_str = match.group(1)
            logger.info("Extracted JSON from code fence")
        else:
            json_str = response_text
            logger.info("Using raw response text as JSON")

        json_str = json_str.replace("\\", "\\\\")
        json_str = json_str.replace("\\\\\"", "\\\"")
        
        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"First JSON decode attempt failed: {e}")
            try:
                json_str = match.group(1) if match else response_text
                json_str = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', json_str)
                data = json.loads(json_str)
                return data
            except Exception as nested_e:
                logger.error(f"Second JSON decode attempt failed: {nested_e}")
                raise ValueError(f"Error decoding JSON from Gemini response: {e}. Additional error: {nested_e}")
    except Exception as e:
        logger.error(f"Error extracting JSON: {e}", exc_info=True)
        raise ValueError(f"Error decoding JSON from Gemini response: {e}")

def process_pdf_with_ocr(pdf_path, api_key=None):
    """
    Process a PDF file with Mistral's OCR service.
    """
    logger.info(f"Starting OCR processing for {pdf_path}")
    
    if api_key is None:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.error("MISTRAL_API_KEY not found in environment variables")
            raise ValueError("MISTRAL_API_KEY not found in environment variables")
    
    client = Mistral(api_key=api_key)
    
    pdf_file = Path(pdf_path)
    if not pdf_file.is_file():
        logger.error(f"PDF file not found: {pdf_path}")
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    logger.info(f"Uploading PDF file to Mistral: {pdf_file.name}")
    uploaded_file = client.files.upload(
        file={
            "file_name": pdf_file.stem,
            "content": pdf_file.read_bytes(),
        },
        purpose="ocr",
    )
    
    logger.info(f"File uploaded successfully with ID: {uploaded_file.id}")
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
    
    logger.info("Starting OCR processing with Mistral")
    pdf_response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest",
        include_image_base64=True
    )
    
    logger.info("OCR processing completed successfully")
    return json.loads(pdf_response.model_dump_json())

def fix_latex_with_gemini(ocr_result):
    """
    Sends the raw OCR data to Gemini to fix LaTeX formatting issues.
    For each page that appears to contain LaTeX, the corrected text is stored under 'fixed_text'.
    """
    logger.info("Starting LaTeX correction using Gemini")
    
    gemini_api_key = os.environ.get("geminiApiKey")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    gemini_client = genai.Client(api_key=gemini_api_key)
    model = 'gemini-2.0-flash'
    
    for page_idx, page in enumerate(ocr_result.get("pages", [])):
        page_content = page.get("text") or page.get("markdown")
        if not page_content or not page_content.strip():
            logger.info(f"Page {page_idx+1} has no text content; skipping LaTeX fix.")
            continue

        if "$" in page_content or r"\(" in page_content or r"\[" in page_content:
            prompt = (
                "The following text is an OCR output that may include errors in LaTeX formatting. "
                "Please review and correct any LaTeX errors so that mathematical formulas are properly formatted. "
                "Return the corrected text without additional commentary.\n\n"
                f"Text: {page_content}"
            )
            try:
                logger.info(f"Sending page {page_idx+1} to Gemini for LaTeX correction")
                response = gemini_client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                fixed_text = response.text.strip()
                logger.info(f"Received LaTeX-corrected text for page {page_idx+1}")
                page["fixed_text"] = fixed_text
            except Exception as e:
                logger.error(f"Error fixing LaTeX on page {page_idx+1}: {e}", exc_info=True)
                page["fixed_text"] = page_content
        else:
            page["fixed_text"] = page_content

    logger.info("Completed LaTeX correction for OCR results")
    print(f"Fixed LaTeX text for {len(ocr_result.get('pages', []))} pages")
    return ocr_result

def process_ocr_results_for_embedding(ocr_result):
    """
    Process OCR results into meaningful semantic chunks using Google Gemini.
    This function uses the LaTeX-corrected text (fixed_text) for chunking.
    """
    logger.info("Starting semantic chunking with Gemini")
    
    gemini_api_key = os.environ.get("geminiApiKey")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    gemini_client = genai.Client(api_key=gemini_api_key)
    model = 'gemini-2.0-flash'
    
    gemini_request_count = 0
    gemini_request_start = time.time()
    
    chunks = []
    
    if "pages" in ocr_result:
        logger.info(f"Processing {len(ocr_result['pages'])} pages for semantic chunking")
        
        for page_idx, page in enumerate(ocr_result["pages"]):
            page_number = page_idx + 1
            logger.info(f"Processing page {page_number} for semantic chunking")
            
            page_content = page.get("fixed_text") or page.get("text") or page.get("markdown")
            
            if page_content and page_content.strip():
                if gemini_request_count >= 15:
                    elapsed = time.time() - gemini_request_start
                    if elapsed < 60:
                        sleep_time = 60 - elapsed
                        logger.info(f"Reached 15 Gemini requests. Sleeping for {sleep_time:.2f} seconds.")
                        time.sleep(sleep_time)
                    gemini_request_count = 0
                    gemini_request_start = time.time()
                
                prompt = (
                    "Analyze the following page content and divide it into distinct sections. "
                    "Treat each section as a self-contained unit of information—this could be a header with its related text, a group of paragraphs, or a list. "
                    "For each section, return the following keys:\n"
                    "  - 'content': The full text content of the section.\n"
                    "  - 'type': The type or category (e.g., heading, paragraph, list).\n"
                    "  - 'meaning': A description of what the section represents (e.g., 'Education details', 'Work experience').\n"
                    "  - 'summary': A brief summary of the key points.\n"
                    "Return a JSON object with a key 'chunks' mapping to an array of these objects.\n\n"
                    f"Page content: {page_content}"
                )
                
                try:
                    logger.info(f"Sending page {page_number} to Gemini for chunking")
                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=prompt,
                    )
                    gemini_request_count += 1
                    logger.info(f"Received Gemini response for page {page_number}")
                    
                    llm_chunks_data = extract_json_from_gemini_response(response.text)
                    logger.info(f"Extracted {len(llm_chunks_data.get('chunks', []))} chunks from page {page_number}")
                    
                    for chunk in llm_chunks_data.get("chunks", []):
                        chunk["page"] = page_number
                        chunks.append(chunk)
                except Exception as e:
                    logger.error(f"Error processing page {page_number} with Gemini: {e}", exc_info=True)
                    chunks.append({
                        "type": "text",
                        "page": page_number,
                        "content": page_content,
                        "meaning": "Full page text without further chunking.",
                        "summary": "Fallback chunk."
                    })
            
            if "tables" in page and page["tables"]:
                logger.info(f"Processing {len(page['tables'])} tables from page {page_number}")
                for table_idx, table in enumerate(page["tables"]):
                    chunks.append({
                        "type": "table",
                        "page": page_number,
                        "table_index": table_idx,
                        "content": table,
                        "meaning": "Table data extracted from the page.",
                        "summary": "Table representation."
                    })
            
            if "images" in page and page["images"]:
                logger.info(f"Processing {len(page['images'])} images from page {page_number}")
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
    
    logger.info(f"Completed semantic chunking with {len(chunks)} total chunks")
    return chunks

# Define Pydantic models for responses and chat messages
class ProcessResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    role: str
    content: Any  # This can be a string or more complex structure

class ChatWithPDFRequest(BaseModel):
    job_id: str
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    content: str

# In-memory job store
jobs = {}

# Background task to process PDF
async def process_pdf_task(job_id: str, file_path: str):
    logger.info(f"Starting background processing task for job: {job_id}")
    try:
        jobs[job_id]["status"] = "processing_ocr"
        logger.info(f"Job {job_id}: Starting OCR processing")
        ocr_results = process_pdf_with_ocr(file_path)
        
        logger.info(f"Job {job_id}: Fixing LaTeX formatting in OCR results")
        ocr_results = fix_latex_with_gemini(ocr_results)
        
        jobs[job_id]["status"] = "processing_chunks"
        logger.info(f"Job {job_id}: Starting semantic chunking")
        chunks = process_ocr_results_for_embedding(ocr_results)
        
        # Create a new dictionary that only returns the fixed text for each page.
        fixed_ocr = {"pages": []}
        for idx, page in enumerate(ocr_results.get("pages", [])):
            fixed_page = {
                "page": idx + 1,
                "fixed_text": page.get("fixed_text", "")
            }
            fixed_ocr["pages"].append(fixed_page)
        
        jobs[job_id]["status"] = "completed"
        logger.info(f"Job {job_id}: Processing completed with {len(chunks)} chunks")
        jobs[job_id]["result"] = {
            "ocr_results": fixed_ocr,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
    except Exception as e:
        logger.error(f"Job {job_id}: Processing failed with error: {e}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "PDF OCR & Analysis API is running"}

@app.post("/process", response_model=ProcessResponse)
async def process_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        logger.info(f"Received file: {file.filename}, content-type: {file.content_type}")
        file_path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            logger.info(f"Saved file to {file_path} ({len(content)} bytes)")
        
        job_id = f"job_{int(time.time())}_{hash(file.filename) % 10000}"
        jobs[job_id] = {"status": "queued"}
        logger.info(f"Created job: {job_id}")
        
        background_tasks.add_task(process_pdf_task, job_id, file_path)
        logger.info(f"Queued background task for job: {job_id}")
        
        return ProcessResponse(
            job_id=job_id,
            status="queued",
            message="PDF processing has been queued."
        )
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    logger.info(f"Checking status for job: {job_id}")
    if job_id not in jobs:
        logger.warning(f"Job not found: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = jobs[job_id]["status"]
    logger.info(f"Job {job_id} status: {status}")
    response = JobStatusResponse(job_id=job_id, status=status)
    
    if status == "completed":
        logger.info(f"Job {job_id} is completed with {len(jobs[job_id]['result']['chunks'])} chunks")
        response.result = jobs[job_id]["result"]
    elif status == "failed":
        logger.error(f"Job {job_id} failed: {jobs[job_id].get('error', 'Unknown error')}")
        response.result = {"error": jobs[job_id].get("error", "Unknown error")}
    
    return response

@app.post("/chat", response_model=ChatResponse)
async def chat_with_pdf_endpoint(chat_request: ChatWithPDFRequest):
    """
    Chat endpoint to interact with the content of an uploaded PDF.
    It expects a job_id referencing a completed PDF processing job as well as a list
    of chat messages from the user.

    The endpoint retrieves the OCR results (fixed text per page) from the processed PDF,
    aggregates the text as context and then combines it with the user-supplied conversation.
    It sends the whole conversation to Mistral's chat API and returns the response.
    
    Example request body:
    {
        "job_id": "job_1691718234_1234",
        "messages": [
            {
                "role": "user",
                "content": "What is the conclusion of the document?"
            }
        ]
    }
    """
    # Verify that the provided job_id exists and is completed.
    job_id = chat_request.job_id
    if job_id not in jobs or jobs[job_id].get("status") != "completed":
        raise HTTPException(status_code=404, detail="Processed PDF not found or not yet completed.")
    
    job_result = jobs[job_id].get("result", {})
    
    # Aggregate the fixed OCR text from each page to provide PDF context.
    ocr_context = ""
    for page in job_result.get("ocr_results", {}).get("pages", []):
        ocr_context += f"Page {page['page']}: {page['fixed_text']}\n"
    
    # Create a system message that supplies the extracted PDF context.
    system_message = {
        "role": "system",
        "content": (
            "You are provided with context from a PDF document. "
            "The following is the extracted text content:\n\n"
            f"{ocr_context}\n\n"
            "Use the above context to answer the subsequent questions."
        )
    }
    
    # Combine the system context message with the messages received in the request.
    conversation_messages = [system_message] + [msg.dict() for msg in chat_request.messages]
    
    try:
        # Retrieve API key from the environment and initialize the Mistral client.
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found in environment variables")
        client = Mistral(api_key=api_key)
        model = "mistral-small-latest"  # Use the desired chat model
        
        chat_response = client.chat.complete(
            model=model,
            messages=conversation_messages
        )
        
        # Return the content of the first chat response.
        return ChatResponse(content=chat_response.choices[0].message.content)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting PDF OCR & Analysis API server")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
