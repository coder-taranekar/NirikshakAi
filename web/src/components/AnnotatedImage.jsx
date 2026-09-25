import { useState } from 'react';
import { MagnifyingGlassPlus, MagnifyingGlassMinus } from '@phosphor-icons/react';

export default function AnnotatedImage({ src, alt = 'Annotated label' }) {
  const [zoom, setZoom] = useState(1);

  if (!src) return (
    <div className="glass-card p-8 flex items-center justify-center text-white/20 text-sm h-64">
      No image available
    </div>
  );

  return (
    <div className="glass-card overflow-hidden relative group">
      <div className="absolute top-3 right-3 z-10 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={() => setZoom(z => Math.min(z + 0.25, 3))} className="p-2 rounded-lg bg-black/60 backdrop-blur text-white/70 hover:text-white transition-all">
          <MagnifyingGlassPlus size={16} />
        </button>
        <button onClick={() => setZoom(z => Math.max(z - 0.25, 0.5))} className="p-2 rounded-lg bg-black/60 backdrop-blur text-white/70 hover:text-white transition-all">
          <MagnifyingGlassMinus size={16} />
        </button>
      </div>
      <div className="overflow-auto max-h-[500px]">
        <img src={src} alt={alt} style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }} className="transition-transform duration-200 max-w-none" />
      </div>
    </div>
  );
}
