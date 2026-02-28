import { useState } from 'react';
import { useWizard } from '@/context/WizardContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import ChatPanel from '@/components/results/ChatPanel';
import SelfCheckBadge from '@/components/generation/SelfCheckBadge';
import { ImageIcon, X } from 'lucide-react';

export default function ImageEditor() {
  const { state } = useWizard();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const selectedImage = state.resultImages.find((img) => img.key === selectedKey);

  if (!selectedKey || !selectedImage) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ImageIcon className="h-4 w-4 text-primary" />
            Edycja obrazu
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Kliknij "Edytuj" na obrazie w galerii, aby otworzyć edytor.
          </p>
          <div className="mt-3 grid grid-cols-4 gap-2">
            {state.resultImages.map((img) => (
              <button
                key={img.key}
                type="button"
                aria-label={`Edytuj obraz: ${img.label || img.key}`}
                className="group relative cursor-pointer overflow-hidden rounded-lg border border-border transition-shadow hover:shadow-md"
                onClick={() => setSelectedKey(img.key)}
              >
                <img
                  src={img.url}
                  alt={img.label || img.key}
                  className="aspect-square w-full object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/30 transition-colors sm:bg-black/0 sm:group-hover:bg-black/30">
                  <span className="text-xs font-medium text-white opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100">
                    Edytuj
                  </span>
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <ImageIcon className="h-4 w-4 text-primary" />
            Edycja: {selectedImage.label || selectedImage.key}
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSelectedKey(null)}
            aria-label="Zamknij edytor"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="overflow-hidden rounded-lg border border-border">
          <img
            src={selectedImage.url}
            alt={selectedImage.label || selectedImage.key}
            className="max-h-80 w-full object-contain"
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{selectedImage.type}</span>
          {selectedImage.selfCheck && (
            <SelfCheckBadge check={selectedImage.selfCheck} />
          )}
        </div>
        <ChatPanel mode="image" imageKey={selectedKey} />
      </CardContent>
    </Card>
  );
}
