// src/components/MarkdownRenderer.tsx
"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import "katex/dist/katex.min.css";

interface MarkdownRendererProps {
  content: string;
}

// This component wraps the table in a scrollable container
const ScrollableTable: React.FC<React.HTMLAttributes<HTMLTableElement>> = ({
  children,
  ...rest
}) => (
  <div className="overflow-x-auto">
    <table
      {...rest}
      className="min-w-full border-collapse border border-gray-300"
    >
      {children}
    </table>
  </div>
);

// Custom table header component with borders
const CustomTableHeader: React.FC<
  React.HTMLAttributes<HTMLTableCellElement>
> = (props) => (
  <th {...props} className="border border-gray-300 p-2 bg-gray-50" />
);

// Custom table cell component with borders
const CustomTableCell: React.FC<
  React.HTMLAttributes<HTMLTableCellElement>
> = (props) => (
  <td {...props} className="border border-gray-300 p-2" />
);

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="prose">
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[rehypeKatex, rehypeRaw]}
        // Override table components with our custom ones
        components={{
          table: ScrollableTable,
          th: CustomTableHeader,
          td: CustomTableCell,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
