/**
 * Plan limits and quota constants
 * Must match backend DAILY_VARIANT_QUOTAS
 */

import type { UserPlan } from '@tasteos/types';

export const PLAN_LIMITS = {
  free: {
    dailyVariantQuota: 3,
    displayName: 'Free',
    price: '$0/month',
  },
  pro: {
    dailyVariantQuota: 30,
    displayName: 'Pro',
    price: '$9.99/month',
  },
  enterprise: {
    dailyVariantQuota: 60,
    displayName: 'Enterprise',
    price: 'Contact us',
  },
} as const;

/**
 * Check if user can generate more variants today
 */
export function canGenerateVariant(plan: UserPlan, usedToday: number): boolean {
  const limit = PLAN_LIMITS[plan]?.dailyVariantQuota;
  if (!limit) return false;
  return usedToday < limit;
}

/**
 * Get remaining variants for today
 */
export function getRemainingVariants(plan: UserPlan, usedToday: number): number {
  const limit = PLAN_LIMITS[plan]?.dailyVariantQuota;
  if (!limit) return 0;
  return Math.max(0, limit - usedToday);
}

/**
 * Format quota display string
 */
export function formatQuotaDisplay(plan: UserPlan, usedToday: number): string {
  const limit = PLAN_LIMITS[plan]?.dailyVariantQuota;
  return `${usedToday}/${limit} variants used today`;
}
