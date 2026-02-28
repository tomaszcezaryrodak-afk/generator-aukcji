import { useWizard } from '@/context/WizardContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import ChatPanel from '@/components/results/ChatPanel';
import { FileText } from 'lucide-react';

function stripHtmlTags(html: string): string {
  // HTML from trusted backend only
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  return doc.body.textContent || '';
}

export default function DescriptionEditor() {
  const { state } = useWizard();

  // For display we strip HTML to plain text; the full HTML is kept in state
  // for BaseLinker export
  const plainText = state.descriptionHtml ? stripHtmlTags(state.descriptionHtml) : '';

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileText className="h-4 w-4 text-primary" />
          Opis produktu
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {plainText ? (
          <div className="whitespace-pre-wrap rounded-lg border border-border bg-background p-4 text-sm leading-relaxed">
            {plainText}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Brak opisu. Wygeneruj opis za pomocą czatu.
          </p>
        )}
        <ChatPanel mode="description" />
      </CardContent>
    </Card>
  );
}
