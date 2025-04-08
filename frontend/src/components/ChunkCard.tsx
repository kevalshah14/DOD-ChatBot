// src/components/ChunkCard.tsx
interface ChunkProps {
  chunk: {
    content: string;
    type: string;
    meaning: string;
    summary: string;
    page: number;
  };
}

export default function ChunkCard({ chunk }: ChunkProps) {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex justify-between items-start mb-2">
        <span className="text-sm font-medium px-2 py-1 bg-blue-100 text-blue-800 rounded">
          {chunk.type}
        </span>
        <span className="text-sm text-gray-500">Page {chunk.page}</span>
      </div>
      
      <h3 className="font-semibold mb-2">{chunk.meaning}</h3>
      
      <div className="mb-3 text-gray-700">
        <p className="text-sm font-medium text-gray-500 mb-1">Summary:</p>
        <p>{chunk.summary}</p>
      </div>
      
      <div className="text-gray-700">
        <p className="text-sm font-medium text-gray-500 mb-1">Content:</p>
        <div className="max-h-40 overflow-y-auto text-sm bg-gray-50 p-3 rounded">
          {chunk.content}
        </div>
      </div>
    </div>
  );
}