"use client";
import { useState } from "react";
import { chatWithPdf, ChatMessage } from "../services/api";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css"; // Import KaTeX CSS for math rendering

interface ChatComponentProps {
  jobId: string;
}

export default function ChatComponent({ jobId }: ChatComponentProps) {
  const [input, setInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    setError(null);

    // Add user's message to the conversation
    const newMessage: ChatMessage = { role: "user", content: input };
    const updatedMessages = [...chatMessages, newMessage];
    setChatMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      // Use the API function to chat with PDF
      const botResponse = await chatWithPdf(jobId, updatedMessages);
      // Append bot's response to the conversation
      setChatMessages((prev) => [...prev, botResponse]);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md mt-8">
      <h2 className="text-2xl font-semibold mb-4">Chat with PDF</h2>

      {/* Chat conversation display */}
      <div className="mb-4 space-y-2">
        {chatMessages.map((msg, index) => (
          <div
            key={index}
            className={`${msg.role === "user" ? "text-right" : "text-left"}`}
          >
            <div
              className={`inline-block p-2 rounded ${
                msg.role === "user" ? "bg-blue-100" : "bg-gray-100"
              }`}
            >
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && (
          <div className="text-left">
            <div className="inline-block bg-gray-100 p-2 rounded">
              <ReactMarkdown>
                {"Bot is typing..."}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Input form for new messages */}
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter your message"
          className="flex-grow border rounded px-3 py-2"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Send
        </button>
      </form>
    </div>
  );
}
