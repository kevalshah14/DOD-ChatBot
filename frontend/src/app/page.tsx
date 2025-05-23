// src/app/page.tsx
"use client";

import { useState, useEffect } from "react";
import { FiLoader, FiCheckCircle, FiAlertCircle } from "react-icons/fi";
import FileUpload from "../components/FileUpload";
import ChunkCard from "../components/ChunkCard";
import { processPdf, checkJobStatus, Chunk } from "../services/api";
import MarkdownRenderer from "../components/MarkdownRenderer";
import ChatComponent from "../components/ChatComponent"; // <-- Import Chat component

interface OCRPage {
  page: number;
  fixed_text: string;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [fixedTextPages, setFixedTextPages] = useState<OCRPage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsLoading(true);
    setError(null);
    setJobId(null);
    setStatus(null);
    setChunks([]);
    setFixedTextPages([]);

    try {
      const data = await processPdf(file);
      setJobId(data.job_id);
      setStatus(data.status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (jobId && status !== "completed" && status !== "failed") {
      intervalId = setInterval(async () => {
        try {
          const jobStatus = await checkJobStatus(jobId);
          setStatus(jobStatus.status);

          if (jobStatus.status === "completed" && jobStatus.result) {
            // Update the chunks state if available
            setChunks(jobStatus.result.chunks);

            // Set fixed OCR pages if available from ocr_results
            if (jobStatus.result.ocr_results?.pages) {
              setFixedTextPages(jobStatus.result.ocr_results.pages);
            }
            clearInterval(intervalId);
          } else if (jobStatus.status === "failed") {
            setError("Processing failed");
            clearInterval(intervalId);
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : "An error occurred");
          clearInterval(intervalId);
        }
      }, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [jobId, status]);

  const getStatusDisplay = () => {
    if (!status) return null;

    let statusText = "";
    let icon = null;

    switch (status) {
      case "queued":
        statusText = "Queued for processing";
        icon = <FiLoader className="animate-spin" />;
        break;
      case "processing_ocr":
        statusText = "Reading and analyzing PDF content";
        icon = <FiLoader className="animate-spin" />;
        break;
      case "processing_chunks":
        statusText = "Chunking document content";
        icon = <FiLoader className="animate-spin" />;
        break;
      case "completed":
        statusText = "Processing complete";
        icon = <FiCheckCircle className="text-green-500" />;
        break;
      case "failed":
        statusText = "Processing failed";
        icon = <FiAlertCircle className="text-red-500" />;
        break;
      default:
        statusText = status;
        icon = <FiLoader className="animate-spin" />;
    }

    return (
      <div className="flex items-center gap-2 font-medium">
        <span>{icon}</span>
        <span>{statusText}</span>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">PDF Analysis Tool</h1>

      {/* File upload form */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <FileUpload onFileSelect={handleFileSelect} />
          <button
            type="submit"
            disabled={!file || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {isLoading ? "Processing..." : "Process PDF"}
          </button>
        </form>
      </div>

      {/* Error message display */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Job status display */}
      {status && (
        <div className="bg-white p-6 rounded-lg shadow-md mb-8">
          <h2 className="text-xl font-semibold mb-2">Job Status</h2>
          {getStatusDisplay()}
          {jobId && <p className="text-sm text-gray-500 mt-1">Job ID: {jobId}</p>}
        </div>
      )}

      {/* Document analysis chunk results */}
      {chunks.length > 0 && (
        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">Document Analysis Results</h2>
          <p className="mb-4 text-gray-600">
            Found {chunks.length} content chunk{chunks.length > 1 ? "s" : ""} in your document
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {chunks.map((chunk, index) => (
              <ChunkCard key={index} chunk={chunk} />
            ))}
          </div>
        </div>
      )}

      {/* Fixed LaTeX (Markdown) results display */}
      {fixedTextPages.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-md mt-8">
          <h2 className="text-2xl font-semibold mb-4">OCR Fixed LaTeX Results</h2>
          {fixedTextPages.map((page) => (
            <div key={page.page} className="mb-6">
              <h3 className="text-xl font-semibold mb-2">Page {page.page}</h3>
              <MarkdownRenderer content={page.fixed_text} />
            </div>
          ))}
        </div>
      )}

      {/* Render the Chat component once processing is complete */}
      {jobId && status === "completed" && (
        <ChatComponent jobId={jobId} />
      )}
    </div>
  );
}
