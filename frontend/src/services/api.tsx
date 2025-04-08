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
    };
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