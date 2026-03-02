import { createContext, useContext, useReducer, useEffect, useRef, useCallback, type ReactNode } from 'react';
import { toast } from 'sonner';
import type { WizardState, WizardAction, WizardStep } from '@/lib/types';

// Session persistence — saves analysis results so page refresh doesn't lose progress
const SESSION_KEY = 'gz_wizard_state';

interface PersistedState {
  step: WizardStep;
  specText: string;
  userNotes: string;
  sessionId: string | null;
  suggestedCategory: string;
  suggestedColors: Record<string, string>;
  suggestedFeatures: Array<{ key: string; value: string }>;
  confirmedColors: Record<string, string>;
  confirmedFeatures: Array<{ key: string; value: string }>;
  mainImageIndex: number;
  productDNA: Record<string, unknown> | null;
}

function saveToSession(state: WizardState) {
  // Only persist pre-generation steps (1-4). Steps 5-6 depend on server state.
  if (state.step >= 5) return;
  // Don't persist if no meaningful data yet
  if (state.step === 1 && state.images.length === 0 && !state.specText) return;

  const persisted: PersistedState = {
    step: state.step,
    specText: state.specText,
    userNotes: state.userNotes,
    sessionId: state.sessionId,
    suggestedCategory: state.suggestedCategory,
    suggestedColors: state.suggestedColors,
    suggestedFeatures: state.suggestedFeatures,
    confirmedColors: state.confirmedColors,
    confirmedFeatures: state.confirmedFeatures,
    mainImageIndex: state.mainImageIndex,
    productDNA: state.productDNA,
  };
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(persisted));
  } catch {
    // quota exceeded — ignore
  }
}

function loadFromSession(): Partial<WizardState> | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as PersistedState;
    // Only restore if analysis was completed (has category)
    if (!data.suggestedCategory) return null;
    // Restore to original step, capped at 4 (steps 5-6 depend on server state).
    // Step 1 requires images (File objects can't be persisted) — skip to 2+ if analysis done.
    const restoredStep = Math.max(2, Math.min(data.step || 2, 4)) as WizardStep;
    return {
      step: restoredStep,
      specText: data.specText,
      userNotes: data.userNotes || '',
      sessionId: data.sessionId || null,
      suggestedCategory: data.suggestedCategory,
      suggestedColors: data.suggestedColors,
      suggestedFeatures: data.suggestedFeatures,
      confirmedColors: data.confirmedColors,
      confirmedFeatures: data.confirmedFeatures,
      mainImageIndex: 0,
      productDNA: data.productDNA || null,
    };
  } catch {
    return null;
  }
}

function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
}

const initialState: WizardState = {
  step: 1,
  images: [],
  mainImageIndex: 0,
  specText: '',
  userNotes: '',
  sessionId: null,
  suggestedCategory: '',
  suggestedColors: {},
  suggestedFeatures: [],
  isAnalyzing: false,
  confirmedColors: {},
  confirmedFeatures: [],
  productDNA: null,
  jobId: null,
  isGenerating: false,
  progress: { step: 0, total: 0, message: '' },
  liveImages: [],
  currentPhase: 'idle',
  phaseImages: [],
  phaseRound: 0,
  selfChecks: [],
  phaseFeedback: '',
  resultImages: [],
  resultSections: null,
  descriptionHtml: '',
  chatMessages: [],
  totalCost: 0,
  modelCosts: {},
  elapsedSeconds: 0,
  generatedAt: '',
  error: null,
};

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, step: action.step };
    case 'SET_IMAGES': {
      // Revoke blob URLs for images being removed (replaced set)
      const newUrls = new Set(action.images.map((img) => img.preview));
      state.images.forEach((img) => {
        if (!newUrls.has(img.preview)) URL.revokeObjectURL(img.preview);
      });
      return { ...state, images: action.images };
    }
    case 'SET_MAIN_IMAGE':
      return { ...state, mainImageIndex: action.index };
    case 'SET_SPEC_TEXT':
      return { ...state, specText: action.text };
    case 'SET_USER_NOTES':
      return { ...state, userNotes: action.notes };
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.sessionId };
    case 'SET_ANALYZING':
      return { ...state, isAnalyzing: action.isAnalyzing };
    case 'SET_ANALYSIS':
      return {
        ...state,
        suggestedCategory: action.data.category,
        suggestedColors: action.data.colors,
        suggestedFeatures: action.data.features,
        confirmedColors: action.data.colors,
        confirmedFeatures: action.data.features,
        isAnalyzing: false,
      };
    case 'SET_CONFIRMED_COLORS':
      return { ...state, confirmedColors: action.colors };
    case 'SET_CONFIRMED_FEATURES':
      return { ...state, confirmedFeatures: action.features };
    case 'SET_PRODUCT_DNA':
      return { ...state, productDNA: action.dna };
    case 'SET_JOB_ID':
      return { ...state, jobId: action.jobId };
    case 'SET_GENERATING':
      // Clear generation artifacts when starting new generation
      if (action.isGenerating) {
        return {
          ...state,
          isGenerating: true,
          liveImages: [],
          selfChecks: [],
          phaseImages: [],
          phaseRound: 0,
          phaseFeedback: '',
          error: null,
        };
      }
      return { ...state, isGenerating: false };
    case 'SET_PROGRESS':
      return { ...state, progress: action.progress };
    case 'ADD_LIVE_IMAGE':
      return { ...state, liveImages: [...state.liveImages, action.image] };
    case 'SET_PHASE':
      return { ...state, currentPhase: action.phase };
    case 'SET_PHASE_IMAGES':
      return { ...state, phaseImages: action.images };
    case 'SET_PHASE_ROUND':
      return { ...state, phaseRound: action.round };
    case 'ADD_SELFCHECK':
      return { ...state, selfChecks: [...state.selfChecks, action.check] };
    case 'SET_PHASE_FEEDBACK':
      return { ...state, phaseFeedback: action.feedback };
    case 'SET_RESULTS':
      return {
        ...state,
        resultImages: action.images,
        resultSections: action.sections,
        descriptionHtml: action.description,
        isGenerating: false,
        currentPhase: 'done',
        step: 6,
      };
    case 'ADD_CHAT_MESSAGE':
      return { ...state, chatMessages: [...state.chatMessages, action.message] };
    case 'SET_DESCRIPTION':
      return { ...state, descriptionHtml: action.html };
    case 'UPDATE_RESULT_IMAGE':
      return {
        ...state,
        resultImages: state.resultImages.map((img) =>
          img.key === action.key ? action.image : img,
        ),
      };
    case 'SET_COST':
      return { ...state, totalCost: action.total, modelCosts: action.perModel };
    case 'SET_ELAPSED':
      return { ...state, elapsedSeconds: action.seconds, generatedAt: action.timestamp };
    case 'SET_ERROR':
      return { ...state, error: action.error };
    case 'CLEAR_CHAT':
      return { ...state, chatMessages: [] };
    case 'RESET':
      state.images.forEach((img) => URL.revokeObjectURL(img.preview));
      clearSession();
      return initialState;
    default:
      return state;
  }
}

interface WizardContextValue {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
  canProceed: () => boolean;
  goNext: () => void;
  goPrev: () => void;
}

const WizardContext = createContext<WizardContextValue | null>(null);

export function WizardProvider({ children }: { children: ReactNode }) {
  const restoredRef = useRef(false);
  const [state, dispatch] = useReducer(wizardReducer, initialState, (init) => {
    const restored = loadFromSession();
    if (restored) {
      restoredRef.current = true;
      return { ...init, ...restored };
    }
    return init;
  });

  // Notify user about restored session (once)
  useEffect(() => {
    if (restoredRef.current) {
      restoredRef.current = false;
      toast.info('Przywrócono dane z poprzedniej sesji. Możesz kontynuować od ostatniego kroku.', { id: 'session-restored' });
    }
  }, []);

  // Persist meaningful state changes to sessionStorage - deps intentionally limited to specific fields
  useEffect(() => {
    saveToSession(state);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.step, state.specText, state.userNotes, state.sessionId, state.suggestedCategory, state.confirmedColors, state.confirmedFeatures, state.productDNA]);

  const canProceed = useCallback(() => {
    switch (state.step) {
      case 1:
        return state.images.length > 0 && state.specText.trim().length > 0;
      case 2:
        return !state.isAnalyzing && state.suggestedCategory !== '';
      case 3:
        return Object.keys(state.confirmedColors).length > 0;
      case 4:
        return state.confirmedFeatures.length > 0;
      case 5:
        return state.currentPhase === 'done';
      default:
        return false;
    }
  }, [state.step, state.images.length, state.specText, state.isAnalyzing, state.suggestedCategory, state.confirmedColors, state.confirmedFeatures.length, state.currentPhase]);

  const goNext = useCallback(() => {
    if (state.step < 6 && canProceed()) {
      dispatch({ type: 'SET_STEP', step: (state.step + 1) as WizardStep });
    }
  }, [state.step, canProceed, dispatch]);

  const goPrev = useCallback(() => {
    if (state.step > 1) {
      dispatch({ type: 'SET_STEP', step: (state.step - 1) as WizardStep });
    }
  }, [state.step, dispatch]);

  return (
    <WizardContext.Provider value={{ state, dispatch, canProceed, goNext, goPrev }}>
      {children}
    </WizardContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useWizard() {
  const ctx = useContext(WizardContext);
  if (!ctx) throw new Error('useWizard must be inside WizardProvider');
  return ctx;
}
