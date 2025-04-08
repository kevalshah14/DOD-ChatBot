import React from 'react';

interface Chunk {
  content: string;
  type: string;
  meaning: string;
  summary: string;
  page: number;
}

interface ChunkCardProps {
  chunk: Chunk;
}

const ChunkCard: React.FC<ChunkCardProps> = ({ chunk }) => {
  return (
    <article 
      className="bg-white p-6 rounded-lg shadow-md" 
      aria-label={`Chunk card of type ${chunk.type}`}
    >
      <header className="flex justify-between items-start mb-2">
        <span
          className="text-sm font-medium px-2 py-1 bg-blue-100 text-blue-800 rounded"
          aria-label="Chunk type"
        >
          {chunk.type}
        </span>
        <span 
          className="text-sm text-gray-500"
          aria-label="Page number"
        >
          Page {chunk.page}
        </span>
      </header>
      
      <h3 className="font-semibold mb-2">{chunk.meaning}</h3>
      
      <section 
        className="mb-3 text-gray-700" 
        aria-labelledby="summary-heading"
      >
        <p 
          id="summary-heading" 
          className="text-sm font-medium text-gray-500 mb-1"
        >
          Summary:
        </p>
        <p>{chunk.summary}</p>
      </section>
      
      <section 
        className="text-gray-700" 
        aria-labelledby="content-heading"
      >
        <p 
          id="content-heading" 
          className="text-sm font-medium text-gray-500 mb-1"
        >
          Content:
        </p>
        <div className="max-h-40 overflow-y-auto text-sm bg-gray-50 p-3 rounded">
          {chunk.content}
        </div>
      </section>
    </article>
  );
};

export default ChunkCard;
