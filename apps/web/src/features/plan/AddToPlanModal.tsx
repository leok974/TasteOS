import { useState } from 'react';
import { format } from 'date-fns';
import { Calendar as CalendarIcon, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAddToPlan } from './hooks';

interface AddToPlanModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  recipeId: string;
  recipeTitle: string;
}

export function AddToPlanModal({ open, onOpenChange, recipeId, recipeTitle }: AddToPlanModalProps) {
  const { addToPlan, isAdding } = useAddToPlan();
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [meal, setMeal] = useState('dinner');
  const [servings, setServings] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await addToPlan({
      recipeId,
      date,
      meal,
      servings: servings ? parseInt(servings, 10) : undefined
    });

    if (success) {
      onOpenChange(false);
      // Reset defaults slightly? No, keeping selection specific might be nice. 
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add to Plan</DialogTitle>
          <DialogDescription>
            Schedule "{recipeTitle}" for a specific meal.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="date" className="text-right">
              Date
            </Label>
            <div className="col-span-3">
                <Input
                    id="date"
                    type="date"
                    required
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                />
            </div>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="meal" className="text-right">
              Meal
            </Label>
             <Select value={meal} onValueChange={setMeal}>
                <SelectTrigger className="w-full col-span-3">
                    <SelectValue placeholder="Select meal" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="lunch">Lunch</SelectItem>
                    <SelectItem value="dinner">Dinner</SelectItem>
                </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="servings" className="text-right">
              Servings
            </Label>
            <Input
              id="servings"
              type="number"
              min="1"
              placeholder="(Optional)"
              value={servings}
              onChange={(e) => setServings(e.target.value)}
              className="col-span-3"
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={isAdding}>
              {isAdding && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save to Plan
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
