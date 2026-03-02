import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const USD_TO_PLN = 3.57;

export function formatPLN(usd: number): string {
  return `${(usd * USD_TO_PLN).toFixed(2)} PLN`;
}

export function formatUSD(usd: number): string {
  return `$${usd.toFixed(3)}`;
}

/**
 * Polish plural forms: 1 → singular, 2-4 → few, 5+ → many
 * Usage: pluralPL(n, 'zdjęcie', 'zdjęcia', 'zdjęć')
 */
export function pluralPL(count: number, one: string, few: string, many: string): string {
  const abs = Math.abs(count);
  if (abs === 1) return one;
  const lastTwo = abs % 100;
  const lastOne = abs % 10;
  if (lastTwo >= 12 && lastTwo <= 14) return many;
  if (lastOne >= 2 && lastOne <= 4) return few;
  return many;
}

/** Platform detection for keyboard hints */
export const isMac = /Mac|iPhone|iPad/.test(navigator.userAgent);

/** Format bytes to human-readable size (e.g., 4.2 MB) */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Compress an image file client-side using Canvas.
 * Strips EXIF data, resizes to maxDimension, outputs JPEG at given quality.
 * Returns original file if already small enough or if compression fails.
 */
export async function compressImage(
  file: File,
  maxDimension = 2048,
  quality = 0.85,
  sizeThreshold = 2 * 1024 * 1024, // 2 MB
): Promise<File> {
  // Skip small files and non-raster formats
  if (file.size <= sizeThreshold) return file;
  if (!file.type.startsWith('image/') || file.type === 'image/svg+xml') return file;

  return new Promise<File>((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(url);
      let { width, height } = img;

      // Only resize if larger than max dimension
      if (width <= maxDimension && height <= maxDimension) {
        // Still run through canvas to strip EXIF
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) { resolve(file); return; }
        ctx.drawImage(img, 0, 0);
        canvas.toBlob(
          (blob) => {
            if (!blob || blob.size >= file.size) { resolve(file); return; }
            resolve(new File([blob], file.name, { type: 'image/jpeg', lastModified: Date.now() }));
          },
          'image/jpeg',
          quality,
        );
        return;
      }

      // Scale down proportionally
      const ratio = Math.min(maxDimension / width, maxDimension / height);
      width = Math.round(width * ratio);
      height = Math.round(height * ratio);

      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) { resolve(file); return; }
      ctx.drawImage(img, 0, 0, width, height);
      canvas.toBlob(
        (blob) => {
          if (!blob) { resolve(file); return; }
          resolve(new File([blob], file.name, { type: 'image/jpeg', lastModified: Date.now() }));
        },
        'image/jpeg',
        quality,
      );
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(file);
    };

    img.src = url;
  });
}

/**
 * Compress multiple image files in parallel.
 * Returns array of compressed files in same order.
 */
export async function compressImages(files: File[]): Promise<File[]> {
  return Promise.all(files.map((f) => compressImage(f)));
}

/** Safe clipboard write with fallback for non-HTTPS contexts */
export async function copyToClipboard(text: string): Promise<boolean> {
  // Prefer modern Clipboard API (requires HTTPS or localhost)
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to legacy fallback
    }
  }
  // Legacy fallback: textarea + execCommand
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

/**
 * Grid arrow-key navigation handler.
 * Attach to onKeyDown of grid items (role="button" or <button>).
 * Detects column count from layout, navigates with arrow keys.
 */
export function handleGridKeyDown(
  e: React.KeyboardEvent<HTMLElement>,
  opts?: { selector?: string; onActivate?: (el: HTMLElement, index: number) => void },
) {
  const key = e.key;
  if (key !== 'ArrowRight' && key !== 'ArrowLeft' && key !== 'ArrowDown' && key !== 'ArrowUp') return;

  const parent = (e.target as HTMLElement).parentElement;
  if (!parent) return;

  const selector = opts?.selector || '[role="button"], button';
  const siblings = Array.from(parent.querySelectorAll<HTMLElement>(selector));
  const idx = siblings.indexOf(e.target as HTMLElement);
  if (idx === -1) return;

  let next = -1;
  if (key === 'ArrowRight') next = Math.min(idx + 1, siblings.length - 1);
  if (key === 'ArrowLeft') next = Math.max(idx - 1, 0);
  if (key === 'ArrowDown' || key === 'ArrowUp') {
    const firstRect = siblings[0].getBoundingClientRect();
    let cols = 1;
    for (let j = 1; j < siblings.length; j++) {
      if (Math.abs(siblings[j].getBoundingClientRect().top - firstRect.top) < 2) cols++;
      else break;
    }
    next = key === 'ArrowDown' ? idx + cols : idx - cols;
    if (next < 0 || next >= siblings.length) next = -1;
  }
  if (next >= 0 && next !== idx) {
    e.preventDefault();
    siblings[next].focus();
    opts?.onActivate?.(siblings[next], next);
  }
}

/** Placeholder SVG for broken images (matches warm beige theme) */
const BROKEN_IMG_SVG = `data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" fill="none"><rect width="200" height="200" fill="%23f5f0e8"/><path d="M85 90h30M100 75v30" stroke="%23c4b89a" stroke-width="2" stroke-linecap="round" opacity=".4"/><text x="100" y="130" text-anchor="middle" fill="%23a0946e" font-family="system-ui" font-size="11" opacity=".5">Brak obrazu</text></svg>',
)}`;

/** Retry image load once with cache-bust, then show placeholder */
export function handleImgError(e: React.SyntheticEvent<HTMLImageElement>) {
  const img = e.currentTarget;
  if (img.dataset.placeholder) return;
  const retried = img.dataset.retried;
  if (!retried) {
    img.dataset.retried = '1';
    const sep = img.src.includes('?') ? '&' : '?';
    img.src = `${img.src}${sep}_r=${Date.now()}`;
    return;
  }
  img.dataset.placeholder = '1';
  img.src = BROKEN_IMG_SVG;
  img.alt = 'Obraz niedostępny';
}
