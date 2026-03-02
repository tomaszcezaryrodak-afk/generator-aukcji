/**
 * Lightweight canvas-based confetti celebration.
 * Fires once and auto-cleans after 3 seconds.
 * No dependencies, brand-themed colors.
 */

type ParticleShape = 'rect' | 'circle' | 'triangle';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  rotation: number;
  rotationSpeed: number;
  shape: ParticleShape;
  wobble: number;
  wobbleSpeed: number;
}

// Brand-themed colors: golds, warm beige, success green
const COLORS = [
  '#a0855a', '#c4a882', '#d4b896', '#8a7a68',
  '#c5a54a', '#b08d5b',
  '#5cb85c', '#4cae4c',
];

const PARTICLE_COUNT = 100;
const DURATION = 3500;
const GRAVITY = 0.11;
const DRAG = 0.986;
const SHAPES: ParticleShape[] = ['rect', 'circle', 'triangle'];

export function fireConfetti() {
  // Respect reduced motion preference
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const canvas = document.createElement('canvas');
  canvas.style.cssText = 'position:fixed;inset:0;z-index:9999;pointer-events:none';
  canvas.width = window.innerWidth * window.devicePixelRatio;
  canvas.height = window.innerHeight * window.devicePixelRatio;
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  document.body.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  if (!ctx) {
    canvas.remove();
    return;
  }
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const w = window.innerWidth;
  const h = window.innerHeight;
  const particles: Particle[] = [];

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: w * 0.5 + (Math.random() - 0.5) * w * 0.5,
      y: h * 0.3,
      vx: (Math.random() - 0.5) * 16,
      vy: -(Math.random() * 12 + 4),
      size: Math.random() * 6 + 3,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: (Math.random() - 0.5) * 0.18,
      shape: SHAPES[Math.floor(Math.random() * SHAPES.length)],
      wobble: Math.random() * Math.PI * 2,
      wobbleSpeed: (Math.random() * 0.05 + 0.02),
    });
  }

  const start = performance.now();

  function animate(now: number) {
    const elapsed = now - start;
    if (elapsed > DURATION) {
      canvas.remove();
      return;
    }

    ctx!.clearRect(0, 0, w, h);
    const fade = Math.max(0, 1 - elapsed / DURATION);

    for (const p of particles) {
      p.vy += GRAVITY;
      p.vx *= DRAG;
      p.wobble += p.wobbleSpeed;
      p.x += p.vx + Math.sin(p.wobble) * 0.5;
      p.y += p.vy;
      p.rotation += p.rotationSpeed;

      ctx!.save();
      ctx!.translate(p.x, p.y);
      ctx!.rotate(p.rotation);
      ctx!.globalAlpha = fade;
      ctx!.fillStyle = p.color;

      switch (p.shape) {
        case 'circle':
          ctx!.beginPath();
          ctx!.arc(0, 0, p.size * 0.4, 0, Math.PI * 2);
          ctx!.fill();
          break;
        case 'triangle':
          ctx!.beginPath();
          ctx!.moveTo(0, -p.size * 0.4);
          ctx!.lineTo(p.size * 0.35, p.size * 0.3);
          ctx!.lineTo(-p.size * 0.35, p.size * 0.3);
          ctx!.closePath();
          ctx!.fill();
          break;
        default:
          ctx!.fillRect(-p.size / 2, -p.size * 0.2, p.size, p.size * 0.4);
      }

      ctx!.restore();
    }

    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}
