/**
 * React hook for managing variant generation state
 */

import { useState, useCallback } from 'react';
import type { RecipeVariant } from '@tasteos/types';
import { generateVariant, QuotaExceededError } from './api';

interface UseVariantsState {
  variants: RecipeVariant[];
  loading: boolean;
  error: string | null;
  quotaError: boolean;
}

interface UseVariantsReturn extends UseVariantsState {
  generate: (
    recipeId: string,
    variantType: string,
    options?: Parameters<typeof generateVariant>[2]
  ) => Promise<RecipeVariant | null>;
  clearError: () => void;
}

/**
 * Hook for managing variant generation
 *
 * Handles loading state, errors, and caching of generated variants
 */
export function useVariants(_recipeId: string): UseVariantsReturn {
  const [state, setState] = useState<UseVariantsState>({
    variants: [],
    loading: false,
    error: null,
    quotaError: false,
  });

  const generate = useCallback(
    async (
      recipeId: string,
      variantType: string,
      options?: Parameters<typeof generateVariant>[2]
    ): Promise<RecipeVariant | null> => {
      setState(prev => ({ ...prev, loading: true, error: null, quotaError: false }));

      try {
        const variant = await generateVariant(recipeId, variantType, options);

        setState(prev => ({
          ...prev,
          variants: [...prev.variants, variant],
          loading: false,
        }));

        return variant;
      } catch (err) {
        const isQuotaError = err instanceof QuotaExceededError;

        setState(prev => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to generate variant',
          quotaError: isQuotaError,
        }));

        return null;
      }
    },
    []
  );

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null, quotaError: false }));
  }, []);

  return {
    ...state,
    generate,
    clearError,
  };
}
