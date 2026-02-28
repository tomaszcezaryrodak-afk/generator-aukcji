import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

interface FeatureRowProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onRemove: () => void;
}

export default function FeatureRow({ label, value, onChange, onRemove }: FeatureRowProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-40 shrink-0 text-sm font-medium">{label}</span>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1"
        aria-label={`Wartość: ${label}`}
      />
      <Button
        variant="ghost"
        size="icon"
        className="h-11 w-11 shrink-0"
        onClick={onRemove}
        aria-label={`Usuń ${label}`}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}
