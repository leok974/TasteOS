/**
 * Import recipe page
 *
 * Allows users to import recipes from URLs or images
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@tasteos/ui';
import { Upload, Link2, Loader2 } from 'lucide-react';
import { importRecipeFromUrl, importRecipeFromImage } from '../lib/api';

export default function ImportRecipe() {
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const navigate = useNavigate();

  const handleUrlImport = async () => {
    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const recipe = await importRecipeFromUrl(url);
      navigate(`/recipes/${recipe.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import recipe from URL');
    } finally {
      setLoading(false);
    }
  };

  const handleImageImport = async () => {
    if (!file) {
      setError('Please select an image');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const recipe = await importRecipeFromImage(file);
      navigate(`/recipes/${recipe.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import recipe from image');
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type.startsWith('image/')) {
        setFile(droppedFile);
        setError(null);
      } else {
        setError('Please drop an image file (JPEG, PNG, etc.)');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Import Recipe</h1>
        <p className="text-gray-600">
          Import recipes from the web or from a photo
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {/* URL Import */}
        <div className="border rounded-lg p-6 bg-white shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Link2 className="w-5 h-5 text-blue-600" />
            <h2 className="text-xl font-semibold">Import from URL</h2>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Paste a link to a recipe from any website
          </p>
          <div className="space-y-4">
            <input
              type="url"
              placeholder="https://example.com/recipe"
              value={url}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUrl(e.target.value)}
              disabled={loading}
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                if (e.key === 'Enter') {
                  handleUrlImport();
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Button
              onClick={handleUrlImport}
              disabled={loading || !url.trim()}
              className="w-full"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing recipe...
                </>
              ) : (
                'Import from URL'
              )}
            </Button>
          </div>
        </div>

        {/* Image Import */}
        <div className="border rounded-lg p-6 bg-white shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Upload className="w-5 h-5 text-green-600" />
            <h2 className="text-xl font-semibold">Import from Image</h2>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Upload a photo of a recipe or recipe card
          </p>
          <div className="space-y-4">
            {/* Drop Zone */}
            <div
              className={`
                border-2 border-dashed rounded-lg p-8 text-center
                transition-colors cursor-pointer
                ${dragActive ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-gray-400'}
                ${file ? 'bg-green-50 border-green-500' : ''}
              `}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <Upload className="w-12 h-12 mx-auto mb-3 text-gray-400" />
              {file ? (
                <p className="text-sm text-gray-700">
                  <span className="font-medium">{file.name}</span>
                  <br />
                  <span className="text-xs text-gray-500">Click to change</span>
                </p>
              ) : (
                <>
                  <p className="text-sm text-gray-600 mb-1">
                    Drag and drop an image here, or click to select
                  </p>
                  <p className="text-xs text-gray-500">
                    JPEG, PNG, or other image formats
                  </p>
                </>
              )}
              <input
                id="file-input"
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            <Button
              onClick={handleImageImport}
              disabled={loading || !file}
              className="w-full"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing image...
                </>
              ) : (
                'Import from Image'
              )}
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-2">💡 Import Tips</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Most recipe websites work great with URL import</li>
          <li>• Image import uses OCR to extract text from photos</li>
          <li>• You can edit and refine imported recipes after creation</li>
        </ul>
      </div>
    </div>
  );
}
