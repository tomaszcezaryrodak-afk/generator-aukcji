import { useEffect, useRef } from 'react';

const SIZE = 32;
const PRIMARY = '#a0855a';
const BG = '#e8e0d5';
const CENTER_BG = '#f7f3ef';
const TEXT_COLOR = '#2d2520';

/**
 * Draws a circular progress donut on the browser favicon during generation.
 * Shows percentage when progress is determinate (total > 0).
 * Shows a subtle partial arc when indeterminate.
 * Restores the original favicon when generation stops.
 */
export function useFaviconProgress(isGenerating: boolean, step: number, total: number) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const originalHref = useRef('');

  // Capture original favicon once
  useEffect(() => {
    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (link && !originalHref.current) {
      originalHref.current = link.href;
    }
  }, []);

  // Draw progress favicon
  useEffect(() => {
    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (!link) return;

    if (!isGenerating) {
      if (originalHref.current && link.href !== originalHref.current) {
        link.href = originalHref.current;
      }
      return;
    }

    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
      canvasRef.current.width = SIZE;
      canvasRef.current.height = SIZE;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const progress = total > 0 ? Math.min(step / total, 1) : 0;
    const cx = SIZE / 2;
    const cy = SIZE / 2;
    const outerR = SIZE / 2 - 1;
    const innerR = SIZE / 4;

    ctx.clearRect(0, 0, SIZE, SIZE);

    // Background ring
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
    ctx.fillStyle = BG;
    ctx.fill();

    // Progress arc (pie slice)
    if (total > 0 && progress > 0) {
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, outerR, -Math.PI / 2, -Math.PI / 2 + progress * Math.PI * 2);
      ctx.closePath();
      ctx.fillStyle = PRIMARY;
      ctx.fill();
    } else if (total === 0) {
      // Indeterminate: small accent arc (~20%)
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, outerR, -Math.PI / 2, -Math.PI / 2 + 0.2 * Math.PI * 2);
      ctx.closePath();
      ctx.fillStyle = PRIMARY;
      ctx.fill();
    }

    // Center hole (donut)
    ctx.beginPath();
    ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
    ctx.fillStyle = CENTER_BG;
    ctx.fill();

    // Percentage text
    if (total > 0) {
      const pct = Math.round(progress * 100);
      ctx.font = `bold ${pct === 100 ? 8 : 10}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = TEXT_COLOR;
      ctx.fillText(`${pct}`, cx, cy + 1);
    }

    link.href = canvas.toDataURL('image/png');
  }, [isGenerating, step, total]);

  // Restore on unmount
  useEffect(() => {
    return () => {
      if (originalHref.current) {
        const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
        if (link) link.href = originalHref.current;
      }
    };
  }, []);
}
