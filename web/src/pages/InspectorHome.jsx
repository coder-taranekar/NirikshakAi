import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadSimple, Link, Camera, CircleNotch, Image, X, ArrowRight } from '@phosphor-icons/react';
import client from '../api/client';

export default function InspectorHome() {
  const [mode, setMode] = useState('upload');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [url, setUrl] = useState('');
  const [state, setState] = useState('');
  const [district, setDistrict] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef(null);
  const navigate = useNavigate();

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setPreview(URL.createObjectURL(f));
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f && f.type.startsWith('image/')) {
      setFile(f);
      setPreview(URL.createObjectURL(f));
    }
  };

  const clearFile = () => { setFile(null); setPreview(null); if(fileRef.current) fileRef.current.value = ''; };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      let res;
      if (mode === 'upload' && file) {
        const form = new FormData();
        form.append('file', file);
        if (state) form.append('state', state);
        if (district) form.append('district', district);
        res = await client.post('/inspections', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      } else if (mode === 'url' && url) {
        res = await client.post('/inspections/url-scan', { source_url: url, state, district });
      } else {
        setError('Please provide an image or URL');
        setLoading(false);
        return;
      }
      navigate(`/inspections/${res.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Scan failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">Scan Label</h1>
        <p className="text-sm text-white/30">Upload a product label image or paste an e-commerce URL to check compliance</p>
      </div>

      {/* Mode Toggle */}
      <div className="flex items-center justify-center gap-2 mb-8">
        {[
          { key: 'upload', icon: Camera, label: 'Image Upload' },
          { key: 'url', icon: Link, label: 'E-commerce URL' },
        ].map(({ key, icon: Icon, label }) => (
          <button key={key} onClick={() => setMode(key)} className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
            mode === key ? 'bg-accent/15 text-accent-light border border-accent/20' : 'text-white/40 hover:text-white/60 border border-transparent hover:bg-white/[0.03]'
          }`}>
            <Icon size={18} weight="duotone" />
            {label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Upload Zone */}
        {mode === 'upload' && (
          <div className="glass-card p-1">
            {preview ? (
              <div className="relative group">
                <img src={preview} alt="Preview" className="w-full max-h-[400px] object-contain rounded-xl" />
                <button type="button" onClick={clearFile} className="absolute top-3 right-3 p-2 rounded-lg bg-black/60 text-white/70 hover:text-white opacity-0 group-hover:opacity-100 transition-all">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <div onClick={() => fileRef.current?.click()} onDrop={handleDrop} onDragOver={(e) => e.preventDefault()}
                className="flex flex-col items-center justify-center gap-4 p-16 rounded-xl border-2 border-dashed border-white/[0.08] hover:border-accent/30 hover:bg-accent/[0.02] transition-all duration-300 cursor-pointer group">
                <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                  <Image size={32} weight="duotone" className="text-accent/60" />
                </div>
                <div className="text-center">
                  <p className="text-sm text-white/50 font-medium">Drop image here or click to browse</p>
                  <p className="text-xs text-white/20 mt-1">JPG, PNG, WEBP up to 10MB</p>
                </div>
              </div>
            )}
            <input ref={fileRef} type="file" accept="image/*" onChange={handleFile} className="hidden" />
          </div>
        )}

        {/* URL Input */}
        {mode === 'url' && (
          <div className="glass-card p-6">
            <label className="text-xs text-white/40 font-medium mb-2 block">Product Listing URL</label>
            <div className="relative">
              <Link size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
              <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.amazon.in/dp/..." className="glass-input w-full pl-10" required={mode === 'url'} />
            </div>
            <p className="text-[10px] text-white/20 mt-2 ml-1">Supports Amazon, Flipkart, JioMart and other major e-commerce platforms</p>
          </div>
        )}

        {/* Location */}
        <div className="glass-card p-6">
          <p className="text-xs text-white/40 font-medium mb-3">Inspection Location (optional)</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] text-white/25 mb-1 block ml-1">State</label>
              <input value={state} onChange={(e) => setState(e.target.value)} placeholder="e.g. Maharashtra" className="glass-input w-full text-sm" />
            </div>
            <div>
              <label className="text-[10px] text-white/25 mb-1 block ml-1">District</label>
              <input value={district} onChange={(e) => setDistrict(e.target.value)} placeholder="e.g. Mumbai Suburban" className="glass-input w-full text-sm" />
            </div>
          </div>
        </div>

        {error && <div className="p-3 rounded-xl bg-danger/10 border border-danger/20 text-danger-light text-sm animate-slide-up">{error}</div>}

        <button type="submit" disabled={loading || (mode === 'upload' && !file) || (mode === 'url' && !url)} className="btn-primary w-full flex items-center justify-center gap-2 py-4 text-base">
          {loading ? <CircleNotch size={22} className="animate-spin" /> : <ArrowRight size={20} weight="bold" />}
          {loading ? 'Analyzing label...' : 'Run Compliance Check'}
        </button>
      </form>
    </div>
  );
}
