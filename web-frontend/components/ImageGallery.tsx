'use client';

import React, { useState } from 'react';

interface ImageData {
  url?: string;
  revised_prompt?: string;
  description?: string;
  alt_text?: string;
  prompt?: string;
  metadata?: any;
}

interface ImageGalleryProps {
  images: ImageData[];
  title?: string;
  showPrompts?: boolean;
  columns?: 1 | 2 | 3 | 4;
  maxHeight?: string;
}

interface ImageModalProps {
  image: ImageData;
  onClose: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  currentIndex: number;
  totalCount: number;
}

/**
 * Modal pro zobrazení obrázku v plné velikosti
 */
const ImageModal: React.FC<ImageModalProps> = ({
  image,
  onClose,
  onNext,
  onPrev,
  currentIndex,
  totalCount
}) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
      <div className="relative max-w-6xl max-h-[90vh] w-full h-full flex items-center justify-center p-4">
        
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-white hover:text-gray-300 z-10"
        >
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Navigation arrows */}
        {totalCount > 1 && (
          <>
            <button
              onClick={onPrev}
              className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white hover:text-gray-300 z-10"
            >
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              onClick={onNext}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white hover:text-gray-300 z-10"
            >
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </>
        )}

        {/* Image */}
        <div className="flex flex-col items-center max-h-full">
          <div className="flex-1 flex items-center justify-center mb-4">
            {image.url ? (
              <img
                src={image.url}
                alt={image.alt_text || image.description || `Image ${currentIndex + 1}`}
                className="max-w-full max-h-full object-contain rounded-lg"
              />
            ) : (
              <div className="text-white text-center">
                <div className="text-6xl mb-4">🖼️</div>
                <p>Obrázek není dostupný</p>
              </div>
            )}
          </div>

          {/* Image info */}
          <div className="bg-black bg-opacity-50 rounded-lg p-4 max-w-2xl w-full">
            <div className="text-white text-sm space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-medium">Obrázek {currentIndex + 1} z {totalCount}</span>
                <button
                  onClick={() => image.url && window.open(image.url, '_blank')}
                  className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-xs"
                >
                  🔗 Otevřít originál
                </button>
              </div>
              
              {(image.revised_prompt || image.prompt) && (
                <div>
                  <span className="font-medium">Prompt:</span>
                  <p className="text-gray-300 mt-1">{image.revised_prompt || image.prompt}</p>
                </div>
              )}
              
              {(image.description || image.alt_text) && (
                <div>
                  <span className="font-medium">Popis:</span>
                  <p className="text-gray-300 mt-1">{image.description || image.alt_text}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Komponenta pro zobrazení galerie obrázků z DALL·E API
 */
const ImageGallery: React.FC<ImageGalleryProps> = ({
  images,
  title = "🎨 Vygenerované obrázky",
  showPrompts = true,
  columns = 3,
  maxHeight = "h-48"
}) => {
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);

  if (!images || images.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-4xl mb-2">🖼️</div>
        <p>Žádné obrázky k zobrazení</p>
      </div>
    );
  }

  const openModal = (index: number) => {
    setSelectedImageIndex(index);
  };

  const closeModal = () => {
    setSelectedImageIndex(null);
  };

  const nextImage = () => {
    if (selectedImageIndex !== null) {
      setSelectedImageIndex((selectedImageIndex + 1) % images.length);
    }
  };

  const prevImage = () => {
    if (selectedImageIndex !== null) {
      setSelectedImageIndex(selectedImageIndex === 0 ? images.length - 1 : selectedImageIndex - 1);
    }
  };

  const getGridCols = () => {
    switch (columns) {
      case 1: return 'grid-cols-1';
      case 2: return 'grid-cols-1 md:grid-cols-2';
      case 3: return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
      case 4: return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
      default: return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (selectedImageIndex !== null) {
      switch (e.key) {
        case 'Escape':
          closeModal();
          break;
        case 'ArrowLeft':
          prevImage();
          break;
        case 'ArrowRight':
          nextImage();
          break;
      }
    }
  };

  return (
    <div className="space-y-4" onKeyDown={handleKeyDown} tabIndex={0}>
      
      {/* Title and stats */}
      <div className="flex items-center justify-between">
        <h5 className="font-semibold text-gray-900 flex items-center gap-2">
          {title}
        </h5>
        <div className="text-sm text-gray-500">
          {images.length} obrázek{images.length !== 1 ? 'ů' : ''}
        </div>
      </div>

      {/* Image grid */}
      <div className={`grid ${getGridCols()} gap-4`}>
        {images.map((image, index) => (
          <div key={index} className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow">
            
            {/* Image */}
            <div className="relative cursor-pointer" onClick={() => openModal(index)}>
              {image.url ? (
                <div className={`relative ${maxHeight} overflow-hidden`}>
                  <img
                    src={image.url}
                    alt={image.alt_text || image.description || `AI generated visual ${index + 1}`}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-200"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                      const parent = target.parentElement;
                      if (parent) {
                        parent.innerHTML = `
                          <div class="flex items-center justify-center h-full bg-gray-100 text-gray-500">
                            <div class="text-center">
                              <div class="text-4xl mb-2">🖼️</div>
                              <p class="text-sm">Obrázek se nepodařilo načíst</p>
                            </div>
                          </div>
                        `;
                      }
                    }}
                  />
                  
                  {/* Overlay with zoom icon */}
                  <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 flex items-center justify-center transition-all duration-200">
                    <div className="opacity-0 hover:opacity-100 transition-opacity">
                      <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                      </svg>
                    </div>
                  </div>
                </div>
              ) : (
                <div className={`flex items-center justify-center ${maxHeight} bg-gray-100 text-gray-500`}>
                  <div className="text-center">
                    <div className="text-4xl mb-2">🖼️</div>
                    <p className="text-sm">Obrázek není dostupný</p>
                  </div>
                </div>
              )}
            </div>

            {/* Image info */}
            <div className="p-3 space-y-2">
              {showPrompts && (image.revised_prompt || image.prompt) && (
                <div>
                  <span className="text-xs font-medium text-gray-600">Prompt:</span>
                  <p className="text-xs text-gray-700 line-clamp-2">
                    {image.revised_prompt || image.prompt}
                  </p>
                </div>
              )}
              
              {(image.description || image.alt_text) && (
                <div>
                  <span className="text-xs font-medium text-gray-600">Popis:</span>
                  <p className="text-xs text-gray-700 line-clamp-2">
                    {image.description || image.alt_text}
                  </p>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => openModal(index)}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs py-1 px-2 rounded"
                >
                  🔍 Zobrazit
                </button>
                {image.url && (
                  <button
                    onClick={() => window.open(image.url, '_blank')}
                    className="bg-gray-600 hover:bg-gray-700 text-white text-xs py-1 px-2 rounded"
                  >
                    🔗
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {selectedImageIndex !== null && (
        <ImageModal
          image={images[selectedImageIndex]}
          onClose={closeModal}
          onNext={nextImage}
          onPrev={prevImage}
          currentIndex={selectedImageIndex}
          totalCount={images.length}
        />
      )}

      {/* Keyboard shortcuts help */}
      {selectedImageIndex !== null && (
        <div className="fixed bottom-4 left-4 bg-black bg-opacity-50 text-white text-xs p-2 rounded z-40">
          <div>ESC - zavřít</div>
          <div>← → - navigace</div>
        </div>
      )}
    </div>
  );
};

export default ImageGallery;