import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

interface ColorChipProps {
  color: string;
  label: string;
  isSelected: boolean;
  onClick: () => void;
}

export default function ColorChip({ color, label, isSelected, onClick }: ColorChipProps) {
  return (
    <button
      type="button"
      className={cn(
        'flex h-11 min-w-[100px] items-center gap-2 rounded-lg border-2 px-3 py-2 text-sm transition-colors cursor-pointer',
        isSelected ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30',
      )}
      onClick={onClick}
      aria-pressed={isSelected}
      aria-label={`Kolor: ${label}`}
    >
      <span
        className="h-5 w-5 shrink-0 rounded-full border border-border"
        style={{ backgroundColor: color }}
      />
      <span className="truncate">{label}</span>
      {isSelected && <Check className="ml-auto h-4 w-4 text-primary" />}
    </button>
  );
}
