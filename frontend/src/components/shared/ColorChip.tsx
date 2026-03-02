import { memo } from 'react';
import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

// Mapa nazw kolorów Granitowe Zlewy → hex
const COLOR_HEX: Record<string, string> = {
  'czarny': '#1a1a1a',
  'czarny metalik': '#2c2c2c',
  'czarny mat': '#1e1e1e',
  'biały': '#f5f5f0',
  'biały połysk': '#ffffff',
  'szary': '#808080',
  'szary metalik': '#6e6e6e',
  'jasny szary': '#c0c0c0',
  'ciemny szary': '#404040',
  'beżowy': '#d4b896',
  'piaskowy': '#c2b280',
  'cappuccino': '#6f4e37',
  'brązowy': '#5c3d2e',
  'czekoladowy': '#3b2212',
  'grafitowy': '#383838',
  'antracyt': '#293133',
  'titanium': '#878681',
  'złoty': '#c5a54a',
  'miedziany': '#b87333',
  'chromowany': '#c0c0c0',
  'stalowy': '#71797e',
  'inox': '#a8a9ad',
  'nikiel': '#727472',
};

function getColorHex(name: string): string {
  const lower = name.toLowerCase().trim();
  if (COLOR_HEX[lower]) return COLOR_HEX[lower];
  // Szukaj częściowego dopasowania
  for (const [key, hex] of Object.entries(COLOR_HEX)) {
    if (lower.includes(key) || key.includes(lower)) return hex;
  }
  // Fallback: spróbuj jako CSS color
  return name;
}

/** Light colors need extra border so they're visible on light backgrounds */
function isLightColor(hex: string): boolean {
  const clean = hex.replace('#', '');
  if (clean.length !== 6) return false;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  // Relative luminance (simplified)
  return (r * 0.299 + g * 0.587 + b * 0.114) > 200;
}

interface ColorChipProps {
  color: string;
  label: string;
  isSelected: boolean;
  onClick: () => void;
}

export default memo(function ColorChip({ color, label, isSelected, onClick }: ColorChipProps) {
  const hex = getColorHex(color);
  const light = isLightColor(hex);

  return (
    <button
      type="button"
      className={cn(
        'flex h-11 min-w-[120px] items-center gap-2.5 rounded-lg border-2 px-3 py-2 text-sm font-medium touch-manipulation transition-all duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 active:scale-95',
        isSelected
          ? 'border-primary bg-primary/5 shadow-sm'
          : 'border-border hover:border-primary/40 hover:shadow-sm opacity-80 hover:opacity-100',
      )}
      onClick={onClick}
      aria-pressed={isSelected}
      aria-label={`Kolor: ${label}`}
    >
      <span
        className={cn(
          'h-6 w-6 shrink-0 rounded-full border shadow-inner transition-transform duration-200',
          isSelected ? 'border-primary/30 scale-110' : 'border-border/50',
          light && 'border-border ring-1 ring-border/30',
        )}
        style={{ backgroundColor: hex }}
      />
      <span className="truncate" title={label}>{label}</span>
      {isSelected && <Check className="ml-auto h-4 w-4 text-primary" />}
    </button>
  );
});
