import { TodayView } from "@/features/plan/TodayView";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ShoppingCart, Utensils, Package } from "lucide-react";

export default function Page() {
  return (
    <main className="container max-w-5xl mx-auto py-8 px-4 space-y-12">

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Good evening, Chef</h1>
          <p className="text-muted-foreground mt-1">Ready to cook something great?</p>
        </div>

      </div>

      {/* Today's Plan */}
      <TodayView />

    </main>
  );
}
