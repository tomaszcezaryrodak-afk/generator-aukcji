import { memo, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { X, ChevronUp, ChevronDown, Pencil, Check } from 'lucide-react';

interface FeatureRowProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onRemove: () => void;
  onLabelChange?: (label: string) => void;
  onMove?: (direction: 'up' | 'down') => void;
  canMoveUp?: boolean;
  canMoveDown?: boolean;
}

export default memo(function FeatureRow({
  label, value, onChange, onRemove,
  onLabelChange, onMove,
  canMoveUp = false, canMoveDown = false,
}: FeatureRowProps) {
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [editLabel, setEditLabel] = useState(label);

  const commitLabel = () => {
    const trimmed = editLabel.trim();
    if (trimmed && trimmed !== label && onLabelChange) {
      onLabelChange(trimmed);
    }
    setIsEditingLabel(false);
  };

  return (
    <div className="group flex items-center gap-1.5 rounded-lg p-1.5 -mx-1.5 transition-colors hover:bg-muted/30">
      {/* Move buttons */}
      {onMove && (
        <div className="flex flex-col opacity-0 group-hover:opacity-60 transition-opacity shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-4 w-4 p-0"
            onClick={() => onMove('up')}
            disabled={!canMoveUp}
            aria-label="Przesuń w górę"
            tabIndex={-1}
          >
            <ChevronUp className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-4 w-4 p-0"
            onClick={() => onMove('down')}
            disabled={!canMoveDown}
            aria-label="Przesuń w dół"
            tabIndex={-1}
          >
            <ChevronDown className="h-3 w-3" />
          </Button>
        </div>
      )}

      {/* Label - click to edit */}
      {isEditingLabel && onLabelChange ? (
        <div className="w-28 shrink-0 sm:w-40 flex items-center gap-1">
          <Input
            value={editLabel}
            onChange={(e) => setEditLabel(e.target.value.slice(0, 100))}
            onBlur={commitLabel}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitLabel();
              if (e.key === 'Escape') { setEditLabel(label); setIsEditingLabel(false); }
            }}
            maxLength={100}
            className="h-7 text-sm"
            autoFocus
            autoComplete="off"
          />
          <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={commitLabel}>
            <Check className="h-3 w-3" />
          </Button>
        </div>
      ) : (
        <span
          className="w-28 shrink-0 text-sm font-medium text-muted-foreground sm:w-40 truncate group/label inline-flex items-center gap-1 cursor-pointer"
          title={`${label} (kliknij aby edytować)`}
          onClick={() => { if (onLabelChange) { setEditLabel(label); setIsEditingLabel(true); } }}
          role={onLabelChange ? 'button' : undefined}
          tabIndex={onLabelChange ? 0 : undefined}
          onKeyDown={(e) => {
            if (onLabelChange && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              setEditLabel(label);
              setIsEditingLabel(true);
            }
          }}
        >
          {label}
          {onLabelChange && (
            <Pencil className="h-2.5 w-2.5 opacity-0 group-hover/label:opacity-40 transition-opacity" />
          )}
        </span>
      )}

      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={200}
        className="flex-1 h-9"
        aria-label={`Wartość: ${label}`}
        autoComplete="off"
      />
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 shrink-0 opacity-40 transition-opacity group-hover:opacity-100"
        onClick={onRemove}
        aria-label={`Usuń ${label}`}
      >
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
});
