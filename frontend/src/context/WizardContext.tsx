import { createContext, useContext, useReducer, type ReactNode } from 'react';
import type { WizardState, WizardAction, WizardStep } from '@/lib/types';

const initialState: WizardState = {
  step: 1,
  images: [],
  mainImageIndex: 0,
  specText: '',
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
  error: null,
};

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, step: action.step };
    case 'SET_IMAGES':
      return { ...state, images: action.images };
    case 'SET_MAIN_IMAGE':
      return { ...state, mainImageIndex: action.index };
    case 'SET_SPEC_TEXT':
      return { ...state, specText: action.text };
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
      return { ...state, isGenerating: action.isGenerating };
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
    case 'SET_ERROR':
      return { ...state, error: action.error };
    case 'RESET':
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
  const [state, dispatch] = useReducer(wizardReducer, initialState);

  const canProceed = () => {
    switch (state.step) {
      case 1:
        return state.images.length > 0;
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
  };

  const goNext = () => {
    if (state.step < 6 && canProceed()) {
      dispatch({ type: 'SET_STEP', step: (state.step + 1) as WizardStep });
    }
  };

  const goPrev = () => {
    if (state.step > 1) {
      dispatch({ type: 'SET_STEP', step: (state.step - 1) as WizardStep });
    }
  };

  return (
    <WizardContext.Provider value={{ state, dispatch, canProceed, goNext, goPrev }}>
      {children}
    </WizardContext.Provider>
  );
}

export function useWizard() {
  const ctx = useContext(WizardContext);
  if (!ctx) throw new Error('useWizard must be inside WizardProvider');
  return ctx;
}
