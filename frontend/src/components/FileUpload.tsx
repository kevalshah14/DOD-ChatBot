// src/components/FileUpload.tsx
import { useState } from "react";
import { FiUpload } from "react-icons/fi";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
}

export default function FileUpload({ onFileSelect }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      onFileSelect(selectedFile);
    }
  };

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 flex flex-col items-center justify-center">
      <FiUpload className="w-8 h-8 text-gray-400 mb-2" />
      <p className="mb-4 text-center text-gray-600">
        {file ? file.name : "Drag and drop a PDF here, or click to select"}
      </p>
      <input
        type="file"
        id="file-upload"
        className="hidden"
        accept="application/pdf"
        onChange={handleFileChange}
      />
      <label
        htmlFor="file-upload"
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors cursor-pointer"
      >
        Select PDF
      </label>
    </div>
  );
}