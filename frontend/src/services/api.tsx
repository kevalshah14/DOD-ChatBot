// src/services/api.ts
export interface Chunk {
  content: string;
  type: string;
  meaning: string;
  summary: string;
  page: number;
}

export interface JobStatus {
  job_id: string;
  status: string;
  result?: {
    chunks: Chunk[];
    total_chunks: number;
    ocr_results?: {
      pages: OCRPage[];
    };
  };
}

export interface OCRPage {
  page: number;
  fixed_text: string;
}

export interface ChatMessage {
  role: string;
  content: string;
}

const API_URL = "http://localhost:8000";

export async function processPdf(file: File): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/process`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Error ${response.status}: ${response.statusText}`);
  }

  return await response.json();
}

export async function checkJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_URL}/status/${jobId}`);

  if (!response.ok) {
    throw new Error(`Error ${response.status}: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Chat with PDF API function.
 *
 * This function sends a POST request to the /chat endpoint, providing the job ID and 
 * conversation messages. The API aggregates the OCR results from the processed PDF and 
 * the conversation, then passes it to the chat model and returns the bot's response.
 *
 * Example request body:
 * {
 *   "job_id": "job_1691718234_1234",
 *   "messages": [
 *     { "role": "user", "content": "What is the conclusion of the document?" }
 *   ]
 * }
 *
 * @param jobId - The reference job id from a completed PDF processing job.
 * @param messages - An array of chat messages forming the conversation history.
 * @returns A ChatMessage containing the bot's response.
 */
export async function chatWithPdf(jobId: string, messages: ChatMessage[]): Promise<ChatMessage> {
  const requestBody = {
    job_id: jobId,
    messages: messages.length > 0 ? [messages[messages.length - 1]] : [],
  };
  
  console.log('Sending to chat API:', requestBody);
  
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    throw new Error(`Error ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  console.log('Received from chat API:', data);
  
  return data;
}
