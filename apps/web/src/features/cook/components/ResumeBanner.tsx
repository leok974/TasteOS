
import React from 'react';
import { RefreshCw, Play } from 'lucide-react';

interface ResumeBannerProps {
    stepIndex: number;
    onResume: () => void;
    onStartOver: () => void;
}

export function ResumeBanner({ stepIndex, onResume, onStartOver }: ResumeBannerProps) {
    if (stepIndex <= 0) return null;

    return (
        <div className="bg-blue-50 border-b border-blue-100 p-4 sticky top-0 z-40">
            <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className="bg-blue-100 p-2 rounded-full">
                        <Play size={20} className="text-blue-600" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-blue-900">Resume Cooking?</h3>
                        <p className="text-sm text-blue-700">
                            You left off at Step {stepIndex + 1}. Would you like to continue?
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3 w-full sm:w-auto">
                    <button
                        onClick={onStartOver}
                        className="flex-1 sm:flex-none px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                        <RefreshCw size={16} />
                        Start Over
                    </button>
                    <button
                        onClick={onResume}
                        className="flex-1 sm:flex-none px-6 py-2 text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-colors"
                    >
                        Resume
                    </button>
                </div>
            </div>
        </div>
    );
}
