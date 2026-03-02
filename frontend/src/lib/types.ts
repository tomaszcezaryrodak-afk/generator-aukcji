export interface UploadedImage {
  file: File;
  preview: string;
  name: string;
}

export interface Feature {
  key: string;
  value: string;
}

export interface GeneratedImage {
  url: string;
  key: string;
  type: 'packshot' | 'composite' | 'lifestyle';
  label: string;
  selfCheck?: SelfCheck;
}

export interface SelfCheck {
  score: number;
  model: string;
  differences: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export interface ResultSections {
  title: string;
  description: string;
  features: Record<string, string>;
  category: string;
}

export interface ProviderInfo {
  name: string;
  status: 'ok' | 'degraded' | 'down';
  lastCheck: string;
}

export type WizardStep = 1 | 2 | 3 | 4 | 5 | 6;

export type GenerationPhase =
  | 'idle'
  | 'dna'
  | 'phase1'
  | 'phase1_approval'
  | 'phase2'
  | 'phase2_approval'
  | 'finalizing'
  | 'done';

export interface WizardState {
  step: WizardStep;

  // Step 1: Upload
  images: UploadedImage[];
  mainImageIndex: number;
  specText: string;
  userNotes: string;

  // Step 2: Analysis
  sessionId: string | null;
  suggestedCategory: string;
  suggestedColors: Record<string, string>;
  suggestedFeatures: Feature[];
  isAnalyzing: boolean;

  // Step 3: Colors
  confirmedColors: Record<string, string>;

  // Step 4: Features
  confirmedFeatures: Feature[];
  productDNA: Record<string, unknown> | null;

  // Step 5: Generate
  jobId: string | null;
  isGenerating: boolean;
  progress: { step: number; total: number; message: string };
  liveImages: GeneratedImage[];
  currentPhase: GenerationPhase;
  phaseImages: GeneratedImage[];
  phaseRound: number;
  selfChecks: SelfCheck[];
  phaseFeedback: string;

  // Step 6: Results
  resultImages: GeneratedImage[];
  resultSections: ResultSections | null;
  descriptionHtml: string;
  chatMessages: ChatMessage[];

  // Global
  totalCost: number;
  modelCosts: Record<string, number>;
  elapsedSeconds: number;
  generatedAt: string;
  error: string | null;
}

export type WizardAction =
  | { type: 'SET_STEP'; step: WizardStep }
  | { type: 'SET_IMAGES'; images: UploadedImage[] }
  | { type: 'SET_MAIN_IMAGE'; index: number }
  | { type: 'SET_SPEC_TEXT'; text: string }
  | { type: 'SET_USER_NOTES'; notes: string }
  | { type: 'SET_SESSION_ID'; sessionId: string }
  | { type: 'SET_ANALYZING'; isAnalyzing: boolean }
  | { type: 'SET_ANALYSIS'; data: { category: string; colors: Record<string, string>; features: Feature[] } }
  | { type: 'SET_CONFIRMED_COLORS'; colors: Record<string, string> }
  | { type: 'SET_CONFIRMED_FEATURES'; features: Feature[] }
  | { type: 'SET_PRODUCT_DNA'; dna: Record<string, unknown> }
  | { type: 'SET_JOB_ID'; jobId: string }
  | { type: 'SET_GENERATING'; isGenerating: boolean }
  | { type: 'SET_PROGRESS'; progress: { step: number; total: number; message: string } }
  | { type: 'ADD_LIVE_IMAGE'; image: GeneratedImage }
  | { type: 'SET_PHASE'; phase: GenerationPhase }
  | { type: 'SET_PHASE_IMAGES'; images: GeneratedImage[] }
  | { type: 'SET_PHASE_ROUND'; round: number }
  | { type: 'ADD_SELFCHECK'; check: SelfCheck }
  | { type: 'SET_PHASE_FEEDBACK'; feedback: string }
  | { type: 'SET_RESULTS'; images: GeneratedImage[]; sections: ResultSections; description: string }
  | { type: 'ADD_CHAT_MESSAGE'; message: ChatMessage }
  | { type: 'SET_DESCRIPTION'; html: string }
  | { type: 'UPDATE_RESULT_IMAGE'; key: string; image: GeneratedImage }
  | { type: 'SET_COST'; total: number; perModel: Record<string, number> }
  | { type: 'SET_ELAPSED'; seconds: number; timestamp: string }
  | { type: 'SET_ERROR'; error: string | null }
  | { type: 'CLEAR_CHAT' }
  | { type: 'RESET' };
