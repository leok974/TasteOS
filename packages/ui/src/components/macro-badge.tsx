/**
 * MacroBadge component
 *
 * Small badge showing protein/carbs/fat in grams
 */

export interface MacroBadgeProps {
  label: string;
  value: number | string;
  unit?: string;
  variant?: 'protein' | 'carbs' | 'fat' | 'calories' | 'neutral';
  className?: string;
}

export function MacroBadge({
  label,
  value,
  unit = 'g',
  variant = 'neutral',
  className = '',
}: MacroBadgeProps) {
  const variantStyles = {
    protein: 'bg-blue-100 text-blue-800 border-blue-200',
    carbs: 'bg-green-100 text-green-800 border-green-200',
    fat: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    calories: 'bg-purple-100 text-purple-800 border-purple-200',
    neutral: 'bg-gray-100 text-gray-800 border-gray-200',
  };

  const style = variantStyles[variant] || variantStyles.neutral;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${style} ${className}`}
    >
      <span className="font-semibold">{value}{unit}</span>
      <span className="opacity-75">{label}</span>
    </span>
  );
}
