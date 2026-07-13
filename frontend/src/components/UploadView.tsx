import React, { useState, useRef } from 'react';
import { Upload, CheckCircle2, AlertCircle, ArrowRight, FileText } from 'lucide-react';
import { uploadResume, ApiError } from '../services/api';
import { ResumeUploadResponse } from '../types/api';

interface UploadViewProps {
  onUploadSuccess: (assignedResumeId: number) => void;
  currentResumeId: number;
}

export const UploadView: React.FC<UploadViewProps> = ({ onUploadSuccess, currentResumeId }) => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ResumeUploadResponse | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (selectedFile: File) => {
    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a valid .pdf file.');
      return;
    }
    setFile(selectedFile);
    setError(null);
    setResponse(null);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please choose a file before uploading.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await uploadResume(file);
      setResponse(res);
      // Pass the assigned/current resume ID counter back to parent
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred while uploading.');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">
          <Upload size={22} className="dropzone-icon" style={{ marginBottom: 0 }} />
          Upload Candidate Resume
        </h2>
        <p className="card-subtitle">
          Ingest a PDF resume into the processing pipeline for extraction and evaluation.
        </p>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          <div>{error}</div>
        </div>
      )}

      {response ? (
        <div className="alert alert-success" style={{ flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <CheckCircle2 size={24} style={{ color: 'var(--success)' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>{response.message}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
                Storage Filename: <code style={{ color: '#fff' }}>{response.filename}</code>
              </div>
            </div>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.25)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={18} />
              <span>{response.original_filename}</span>
            </div>
            <span style={{ color: 'var(--text-muted)' }}>{formatBytes(response.size_bytes)}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onUploadSuccess(currentResumeId)}
            >
              Proceed to Screening
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      ) : (
        <>
          <div
            className={`dropzone ${isDragging ? 'active' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              style={{ display: 'none' }}
              onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
            />
            <Upload size={36} className="dropzone-icon" />
            <div className="dropzone-title">
              {file ? file.name : 'Drag & drop resume PDF here, or click to browse'}
            </div>
            <div className="dropzone-desc">
              {file ? `${formatBytes(file.size)} — Ready to upload` : 'Only single .pdf documents are supported'}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!file || loading}
              onClick={handleUpload}
            >
              {loading ? (
                <>
                  <div className="spinner" />
                  Uploading & Parsing...
                </>
              ) : (
                'Upload Resume'
              )}
            </button>
          </div>
        </>
      )}
    </div>
  );
};
