
import { MealPlan, PlanEntry } from './hooks';
import { PlanCell } from './PlanCell';
import { format, parseISO, addDays } from 'date-fns';

interface PlanGridProps {
    plan: MealPlan;
}

export function PlanGrid({ plan }: PlanGridProps) {
    // Group entries by date -> type
    // Plan starts on Monday.
    const weekStart = parseISO(plan.week_start);

    const days = Array.from({ length: 7 }).map((_, i) => {
        const date = addDays(weekStart, i);
        const dateStr = format(date, 'yyyy-MM-dd');
        return {
            date,
            dateLabel: format(date, 'EEE, MMM d'),
            dateStr,
            lunch: plan.entries.find(e => e.date === dateStr && e.meal_type === 'lunch'),
            dinner: plan.entries.find(e => e.date === dateStr && e.meal_type === 'dinner'),
        };
    });

    return (
        <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
            {days.map((day) => (
                <div key={day.dateStr} className="flex flex-col gap-3">
                    <div className="text-center pb-2 border-b">
                        <div className="font-semibold">{format(day.date, 'EEEE')}</div>
                        <div className="text-xs text-muted-foreground">{format(day.date, 'MMM d')}</div>
                    </div>

                    {/* Lunch */}
                    <div className="flex-1 min-h-[160px]">
                        <span className="text-xs font-medium text-muted-foreground mb-1 block uppercase tracking-wider">Lunch</span>
                        <PlanCell entry={day.lunch} type="lunch" />
                    </div>

                    {/* Dinner */}
                    <div className="flex-1 min-h-[160px]">
                        <span className="text-xs font-medium text-muted-foreground mb-1 block uppercase tracking-wider">Dinner</span>
                        <PlanCell entry={day.dinner} type="dinner" />
                    </div>
                </div>
            ))}
        </div>
    );
}
