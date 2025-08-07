'use client'

import { useEffect, useState, useRef } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import ImageGallery from '../../../../components/ImageGallery'

interface WorkflowResult {
  status: string
  result?: any
  start_time?: string
  end_time?: string | null
  current_phase?: string
  current_activity_type?: string
  elapsed_seconds?: number
  activity_elapsed_seconds?: number
  activity_attempt?: number
  is_long_running?: boolean
  warning?: boolean
  diagnostic_error?: string
  stage_logs?: Array<{
    stage: string
    status: string
    timestamp: number
    duration?: number
    error?: string
    output?: any
  }>
}

interface AssistantCardProps {
  stage: any
  index: number
  isExpanded: boolean
  onToggleExpand: () => void
  showOutputModal: (output: any, stageName: string) => void
  retryPublishScript: (stageName: string) => void
  downloadPublishOutput: (output: any, format: 'html' | 'json') => void
}

interface OutputModalProps {
  isOpen: boolean
  onClose: () => void
  output: any
  stageName: string
}

// Function to parse image output for ImageRendererAssistant
const parseImageOutput = (output: any): { images: any[], hasImages: boolean } => {
  if (!output) return { images: [], hasImages: false };
  
  try {
    let parsedOutput = output;
    
    if (typeof output === 'string') {
      parsedOutput = JSON.parse(output);
    }
    
    // 🔧 OPRAVA: ImageRendererAssistant má strukturu { images: [...] }
    if (parsedOutput.images && Array.isArray(parsedOutput.images)) {
      return {
        images: parsedOutput.images,
        hasImages: true
      };
    }
    
    if (parsedOutput.generated_images || parsedOutput.image_urls) {
      return {
        images: parsedOutput.generated_images || parsedOutput.image_urls,
        hasImages: true
      };
    }
    
    if (Array.isArray(parsedOutput) && parsedOutput.length > 0 && parsedOutput[0].url) {
      return {
        images: parsedOutput,
        hasImages: true
      };
    }
    
  } catch (e) {
    // Pokud parsování selže, return false
  }
  
  return { images: [], hasImages: false };
};

const OutputModal = ({ isOpen, onClose, output, stageName }: OutputModalProps) => {
  if (!isOpen) return null;

  // Function to copy output to clipboard with proper error handling
  const copyOutput = async () => {
    try {
      const textToCopy = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
      
      // Check if clipboard API is available
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(textToCopy);
        alert('✅ Výstup zkopírován do schránky!');
      } else {
        // Browser doesn't support clipboard API - show text for manual copy
        prompt('📋 Zkopíruj tento text ručně (Ctrl+C):', textToCopy);
      }
    } catch (error) {
      console.error('❌ Clipboard error:', error);
      // If clipboard fails, show text for manual copy
      const textToCopy = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
      prompt('📋 Zkopíruj tento text ručně (Ctrl+C):', textToCopy);
    }
  };

  // Function to render image previews
  const renderImagePreviews = (images: string | string[]) => {
    const imageUrls = Array.isArray(images) ? images : [images];
    
    return (
      <div className="mb-4">
        <h5 className="font-medium mb-3 text-gray-700">🖼️ Generované obrázky:</h5>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {imageUrls.map((url, index) => (
            <div key={index} className="relative group">
              <img 
                src={url} 
                alt={`AI generated visualization ${index + 1}`}
                className="w-full h-auto max-w-full rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => window.open(url, '_blank')}
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                }}
              />
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => window.open(url, '_blank')}
                  className="bg-black bg-opacity-50 text-white p-1 rounded text-xs hover:bg-opacity-70"
                >
                  🔍 Otevřít
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const formatOutput = (output: any) => {
    if (!output) return <div className="text-gray-500">Žádný výstup k dispozici</div>;

    // Check for image URLs first
    let hasImages = false;
    let imageContent = null;
    
    if (typeof output === 'object') {
      // Check for image_url field
      if (output.image_url && typeof output.image_url === 'string') {
        hasImages = true;
        imageContent = renderImagePreviews(output.image_url);
      }
      // Check for images array
      else if (output.images && Array.isArray(output.images) && output.images.length > 0) {
        hasImages = true;
        // Handle array of objects with url property (ImageRenderer format)
        const imageUrls = output.images.map(item => 
          typeof item === 'string' ? item : item.url || item
        ).filter(url => url && typeof url === 'string');
        
        if (imageUrls.length > 0) {
          imageContent = renderImagePreviews(imageUrls);
        } else {
          imageContent = renderImagePreviews(output.images);
        }
      }
      // Check for nested image URLs in various formats
      else if (output.generated_images) {
        if (typeof output.generated_images === 'string') {
          hasImages = true;
          imageContent = renderImagePreviews(output.generated_images);
        } else if (Array.isArray(output.generated_images)) {
          hasImages = true;
          imageContent = renderImagePreviews(output.generated_images);
        }
      }
    }

    // Try to detect format
    if (typeof output === 'string') {
      // Check if it's JSON
      try {
        const parsed = JSON.parse(output);
        
        // Check for images in parsed JSON
        let parsedImages = null;
        if (parsed.image_url && typeof parsed.image_url === 'string') {
          parsedImages = renderImagePreviews(parsed.image_url);
        } else if (parsed.images && Array.isArray(parsed.images) && parsed.images.length > 0) {
          parsedImages = renderImagePreviews(parsed.images);
        } else if (parsed.generated_images) {
          if (typeof parsed.generated_images === 'string') {
            parsedImages = renderImagePreviews(parsed.generated_images);
          } else if (Array.isArray(parsed.generated_images)) {
            // Handle array of objects with url property
            const imageUrls = parsed.generated_images.map(item => 
              typeof item === 'string' ? item : item.url || item
            ).filter(url => url);
            if (imageUrls.length > 0) {
              parsedImages = renderImagePreviews(imageUrls);
            }
          }
        } else if (parsed.image_urls && Array.isArray(parsed.image_urls)) {
          parsedImages = renderImagePreviews(parsed.image_urls);
        }
        
        return (
          <div>
            {parsedImages}
            <h5 className="font-medium mb-3 text-gray-700">📄 JSON Output:</h5>
            <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-sm overflow-auto max-h-96 font-mono">
              {JSON.stringify(parsed, null, 2)}
            </pre>
          </div>
        );
      } catch {
        // Check if it contains markdown-like syntax
        if (output.includes('##') || output.includes('**') || output.includes('[') && output.includes('](')) {
          return (
            <div>
              {hasImages && imageContent}
              <h5 className="font-medium mb-3 text-gray-700">📝 Markdown Output:</h5>
              <div className="bg-white border border-gray-200 p-4 rounded-lg max-h-96 overflow-auto prose prose-sm max-w-none">
                <div dangerouslySetInnerHTML={{__html: output.replace(/\n/g, '<br/>')}} />
              </div>
            </div>
          );
        }
        
        // Plain text
        return (
          <div>
            {hasImages && imageContent}
            <h5 className="font-medium mb-3 text-gray-700">📄 Text Output:</h5>
            <pre className="bg-gray-50 border border-gray-200 p-4 rounded-lg text-sm overflow-auto max-h-96 whitespace-pre-wrap font-mono">
              {output}
            </pre>
          </div>
        );
      }
    } else {
      // Object/array
      return (
        <div>
          {hasImages && imageContent}
          <h5 className="font-medium mb-3 text-gray-700">📊 Structured Data:</h5>
          <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-sm overflow-auto max-h-96 font-mono">
            {JSON.stringify(output, null, 2)}
          </pre>
        </div>
      );
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl max-h-[90vh] w-full overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-xl font-semibold text-gray-900">
            🤖 Výstup asistenta: {stageName}
          </h3>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
          >
            ×
          </button>
        </div>
        <div className="p-6 overflow-auto max-h-[70vh]">
          {formatOutput(output)}
        </div>
        <div className="flex justify-between p-6 border-t border-gray-200">
          <button
            onClick={copyOutput}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
          >
            📋 Zkopírovat výstup
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Zavřít
          </button>
        </div>
      </div>
    </div>
  );
};

const AssistantCard = ({ stage, index, isExpanded, onToggleExpand, showOutputModal, retryPublishScript, downloadPublishOutput }: AssistantCardProps) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'bg-green-50 border-green-200 shadow-sm'
      case 'FAILED': return 'bg-red-50 border-red-200 shadow-sm'
      case 'STARTED': 
      case 'RUNNING': return 'bg-blue-50 border-blue-200 shadow-sm'
      case 'TIMED_OUT': return 'bg-orange-50 border-orange-200 shadow-sm'
      case 'PENDING': return 'bg-gray-50 border-gray-300 shadow-sm'
      default: return 'bg-gray-50 border-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '✅'
      case 'FAILED': return '❌'
      case 'STARTED':
      case 'RUNNING': return '🔄'
      case 'TIMED_OUT': return '⏰'
      case 'PENDING': return '⏳'
      default: return '⚠️'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'Dokončeno'
      case 'FAILED': return 'Selhalo'
      case 'STARTED': return 'Spuštěno'
      case 'RUNNING': return 'Probíhá...'
      case 'TIMED_OUT': return 'Timeout'
      case 'PENDING': return 'Čeká na spuštění'
      default: return status
    }
  }

  const getProgressColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'bg-green-500'
      case 'FAILED': return 'bg-red-500'
      case 'RUNNING': return 'bg-blue-500'
      case 'TIMED_OUT': return 'bg-orange-500'
      case 'PENDING': return 'bg-gray-400'
      default: return 'bg-gray-300'
    }
  }

  // Zkrácení názvu asistenta pro lepší zobrazení
  const formatAssistantName = (name: string) => {
    return name.replace('Assistant', '').replace('_', ' ');
  };

  return (
    <div className={`border rounded-xl transition-all duration-200 hover:shadow-md ${getStatusColor(stage.status)}`}>
      {/* Header Card */}
      <div className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Status Icon */}
            <div className="flex items-center">
              <span className="text-2xl">
                {getStatusIcon(stage.status)}
                {stage.status === 'RUNNING' && (
                  <span className="inline-block w-2 h-2 bg-blue-500 rounded-full animate-pulse ml-1"></span>
                )}
              </span>
            </div>
            
            {/* Assistant Info */}
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900 text-lg">
                {stage.assistant_name || formatAssistantName(stage.stage)}
              </h4>
              {stage.assistant_description && (
                <p className="text-sm text-gray-500 mt-1">
                  {stage.assistant_description}
                </p>
              )}
              <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                {stage.status !== 'PENDING' ? (
                  <>
                <span>
                  {new Date(stage.timestamp * 1000).toLocaleTimeString('cs-CZ')}
                </span>
                {stage.duration && (
                  <span className="flex items-center gap-1">
                    ⏱️ {stage.duration.toFixed(1)}s
                      </span>
                    )}
                  </>
                ) : (
                  <span className="text-gray-500">
                    ⏳ Čeká na spuštění
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Status Badge & Actions */}
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              stage.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
              stage.status === 'FAILED' ? 'bg-red-100 text-red-800' :
              stage.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' :
              stage.status === 'TIMED_OUT' ? 'bg-orange-100 text-orange-800' :
              stage.status === 'PENDING' ? 'bg-gray-100 text-gray-600' :
              'bg-gray-100 text-gray-800'
            }`}>
              {getStatusText(stage.status)}
            </span>

            {/* Output Button */}
            {(stage.output || stage.stage_output) && (
              <button
                onClick={() => showOutputModal(stage.output || stage.stage_output, stage.stage)}
                className="px-3 py-1 bg-blue-600 text-white text-xs rounded-md hover:bg-blue-700 transition-colors"
              >
                📄 Zobrazit výstup
              </button>
            )}

            {/* PublishScript Special Buttons */}
            {(stage.stage.toLowerCase().includes('publish') || stage.stage.toLowerCase().includes('publishscript')) && (stage.status === 'COMPLETED' || stage.status === 'FAILED') && (
              <div className="flex gap-2">
                <button
                  onClick={() => downloadPublishOutput(stage.output || stage.stage_output, 'html')}
                  className="px-3 py-1 bg-green-600 text-white text-xs rounded-md hover:bg-green-700 transition-colors"
                >
                  📄 Stáhnout HTML
                </button>
                <button
                  onClick={() => downloadPublishOutput(stage.output || stage.stage_output, 'json')}
                  className="px-3 py-1 bg-purple-600 text-white text-xs rounded-md hover:bg-purple-700 transition-colors"
                >
                  📊 Stáhnout JSON
                </button>
                <button
                  onClick={() => retryPublishScript(stage.stage)}
                  className="px-3 py-1 bg-orange-600 text-white text-xs rounded-md hover:bg-orange-700 transition-colors"
                  title="Regenerovat PublishScript s aktuálními daty asistentů"
                >
                  🔧 Regenerovat
                </button>
              </div>
            )}

            {/* Expand Button */}
            <button
              onClick={onToggleExpand}
              className="text-gray-400 hover:text-gray-600 text-lg"
            >
              {isExpanded ? '▼' : '▶'}
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-500 ${getProgressColor(stage.status)}`}
              style={{ 
                width: stage.status === 'COMPLETED' ? '100%' : 
                       stage.status === 'RUNNING' ? '60%' : 
                       stage.status === 'FAILED' || stage.status === 'TIMED_OUT' ? '100%' : '0%' 
              }}
            />
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t bg-white bg-opacity-50 p-5 space-y-4">
          {/* Error Message */}
          {stage.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="text-red-500 text-lg">⚠️</span>
                <div className="flex-1">
                  <h5 className="font-medium text-red-800 mb-2">Došlo k chybě</h5>
                  <p className="text-sm text-red-700 mb-3">{stage.error}</p>
                  
                  {/* Retry UI Slot */}
                  <div className="pt-3 border-t border-red-200">
                    {(stage.stage.toLowerCase().includes('publish') || stage.stage.toLowerCase().includes('publishscript')) ? (
                      <button 
                        onClick={() => retryPublishScript(stage.stage)}
                        className="px-4 py-2 bg-orange-600 text-white text-sm rounded-lg hover:bg-orange-700 transition-colors"
                        title="Spustit pouze PublishScript znovu"
                      >
                        🔧 Znovu spustit PublishScript
                      </button>
                    ) : (
                    <button 
                      className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                      disabled
                      title="Retry funkcionalita bude implementována později"
                    >
                      🔄 Opakovat (neimplementováno)
                    </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Status-specific content */}
          {stage.status === 'RUNNING' && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-3 text-blue-700">
                <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                <span className="font-medium">Asistent právě pracuje...</span>
              </div>
            </div>
          )}

          {stage.status === 'TIMED_OUT' && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <div className="flex items-center gap-3 text-orange-700">
                <span className="text-lg">⏰</span>
                <span className="font-medium">Asistent překročil časový limit</span>
              </div>
            </div>
          )}

          {/* Output placeholder for completed but no output */}
          {!stage.output && !stage.stage_output && !stage.error && stage.status === 'COMPLETED' && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
              <span className="text-2xl mb-2 block">📭</span>
              <p>Výstup není dostupný nebo došlo k chybě při generování</p>
            </div>
          )}

          {/* Waiting state */}
          {stage.status === 'PENDING' && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-3 text-gray-600">
                <span className="text-lg">⏳</span>
                <span className="font-medium">Čeká na předchozí asistenta...</span>
              </div>
            </div>
          )}

          {/* 🔧 OPRAVA: Zobrazení výstupu asistentů - hledáme stage_output */}
          {(stage.output || stage.stage_output) && stage.status === 'COMPLETED' && (
            <div className="space-y-3">
              <h5 className="font-semibold text-gray-900 border-b pb-2">📤 Výstup asistenta:</h5>
              
              {/* 🎨 Speciální handling pro ImageRendererAssistant */}
              {(stage.stage?.trim() === 'ImageRendererAssistant' || stage.stage?.includes('ImageRenderer') || stage.stage?.includes('Image')) && (() => {
                const currentOutput = stage.output || stage.stage_output;
                const { images, hasImages } = parseImageOutput(currentOutput);
                if (hasImages) {
                  return (
                    <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4">
                      <ImageGallery images={images} title="🎨 Vygenerované obrázky" />
                    </div>
                  );
                }
              })()}
              
              {/* JSON output */}
              <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                <pre className="text-xs whitespace-pre-wrap break-words font-mono">
                  {typeof (stage.output || stage.stage_output) === 'string' 
                    ? (stage.output || stage.stage_output)
                    : JSON.stringify((stage.output || stage.stage_output), null, 2)}
                </pre>
              </div>
              
              {/* Copy button */}
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    const content = typeof (stage.output || stage.stage_output) === 'string' 
                      ? (stage.output || stage.stage_output)
                      : JSON.stringify((stage.output || stage.stage_output), null, 2);
                    await navigator.clipboard.writeText(content);
                    alert('✅ Výstup zkopírován do schránky!');
                  }}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                >
                  📋 Kopírovat
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const PipelineProgress = ({ stages, assistantOrder, expandedAssistants, toggleAssistantExpand, showOutputModal, retryPublishScript }: {
  stages: any[]
  assistantOrder: string[]
  expandedAssistants: Set<number>
  toggleAssistantExpand: (index: number) => void
  showOutputModal: (output: any, stageName: string) => void
  retryPublishScript: (stageName: string) => void
}) => {
  // Dynamické seřazení podle pořadí z databáze/workflow dat
  const sortedStages = [...stages].sort((a, b) => {
    const indexA = assistantOrder.indexOf(a.stage);
    const indexB = assistantOrder.indexOf(b.stage);
    
    // Pokud asistent není v seznamu, umístí se na konec
    if (indexA === -1 && indexB === -1) return 0;
    if (indexA === -1) return 1;
    if (indexB === -1) return -1;
    
    return indexA - indexB;
  });

  const completedCount = sortedStages.filter(s => s.status === 'COMPLETED').length;
  const failedCount = sortedStages.filter(s => s.status === 'FAILED' || s.status === 'TIMED_OUT').length;

  // 🔧 OPRAVA: Definice downloadPublishOutput funkce před renderováním
  const downloadPublishOutput = (output: any, format: 'html' | 'json') => {
    try {
      let content = '';
      let filename = '';
      let mimeType = '';

      if (format === 'html') {
        // Extract HTML content from PublishScript output
        if (output && output.contentHtml && typeof output.contentHtml === 'string') {
          content = output.contentHtml;
        } else if (output && output.data && output.data.contentHtml && typeof output.data.contentHtml === 'string') {
          content = output.data.contentHtml;
        } else if (output && output.output && typeof output.output === 'string') {
          content = output.output;
        } else if (output && output.html) {
          content = output.html;
        } else {
          content = JSON.stringify(output, null, 2);
          console.warn('HTML obsah nenalezen, stahuje se jako JSON:', output);
        }
        filename = `article_${new Date().toISOString().slice(0,10)}.html`;
        mimeType = 'text/html';
      } else {
        // JSON format
        content = JSON.stringify(output, null, 2);
        filename = `article_data_${new Date().toISOString().slice(0,10)}.json`;
        mimeType = 'application/json';
      }

      // Create and download file
      const blob = new Blob([content], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      console.log(`✅ Downloaded ${format.toUpperCase()} file:`, filename);
    } catch (error) {
      console.error('❌ Error downloading file:', error);
      alert('Chyba při stahování souboru');
    }
  };

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-bold text-gray-900">🤖 Pipeline Asistentů</h3>
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-600">
            <span className="font-medium">{completedCount}</span> / {sortedStages.length} dokončeno
          </div>
          {failedCount > 0 && (
            <div className="text-sm text-red-600">
              <span className="font-medium">{failedCount}</span> selhalo
            </div>
          )}
        </div>
      </div>

      {/* Overall Progress Bar */}
      <div className="mb-6">
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-gradient-to-r from-blue-500 to-green-500 h-3 rounded-full transition-all duration-700"
            style={{ width: `${(completedCount / sortedStages.length) * 100}%` }}
          />
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Celkový progress: {Math.round((completedCount / sortedStages.length) * 100)}%
        </div>
      </div>

      <div className="space-y-4">
        {sortedStages.map((stage, index) => (
          <AssistantCard
            key={`${stage.stage}-${index}`}
            stage={stage}
            index={index}
            isExpanded={expandedAssistants.has(index)}
            onToggleExpand={() => toggleAssistantExpand(index)}
            showOutputModal={showOutputModal}
            retryPublishScript={retryPublishScript}
            downloadPublishOutput={downloadPublishOutput}
          />
        ))}
      </div>

      {sortedStages.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <span className="text-4xl mb-4 block">🤖</span>
          <p className="text-lg">Pipeline asistentů se ještě nespustila</p>
          <p className="text-sm">Výsledky se zobrazí, jakmile workflow začne zpracovávat jednotlivé fáze</p>
        </div>
      )}
    </div>
  );
};

export default function WorkflowDetailPage() {
  const params = useParams()
  
  // State for client-side URL params
  const [clientUrlParams, setClientUrlParams] = useState<{workflow_id: string | null, run_id: string | null}>({
    workflow_id: null,
    run_id: null
  });
  const [isClient, setIsClient] = useState(false);
  
  // Extract parameters from window.location (client-side only)
  useEffect(() => {
    console.log('🔍 CLIENT INITIALIZATION START');
    setIsClient(true);
    
    if (typeof window !== 'undefined') {
      const path = window.location.pathname;
      console.log('🔍 CLIENT WINDOW PATH:', path);
      
      // Extract from path: /workflows/[workflow_id]/[run_id]
      const matches = path.match(/\/workflows\/([^\/]+)\/([^\/]+)/);
      if (matches) {
        const extracted = {
          workflow_id: decodeURIComponent(matches[1]),
          run_id: decodeURIComponent(matches[2])
        };
        console.log('🔍 EXTRACTED FROM URL:', extracted);
        setClientUrlParams(extracted);
        console.log('✅ CLIENT URL PARAMS SET');
      } else {
        console.log('❌ NO MATCH FOUND IN URL PATH');
      }
    }
  }, []);
  
  // Determine final params: try useParams first, fallback to client URL extraction
  let workflow_id = params.workflow_id as string;
  let run_id = params.run_id as string;
  
  // If useParams failed and we have client-side extracted params, use those
  if ((!workflow_id || !run_id || workflow_id === 'undefined' || run_id === 'undefined') && isClient) {
    console.log('❌ useParams() failed, using client URL extraction');
    workflow_id = clientUrlParams.workflow_id || 'undefined';
    run_id = clientUrlParams.run_id || 'undefined';
  }
  
  // Additional decoding if needed
  if (workflow_id && workflow_id !== 'undefined') {
    try {
      workflow_id = decodeURIComponent(workflow_id);
    } catch (e) {
      console.warn('Failed to decode workflow_id:', workflow_id);
    }
  }
  if (run_id && run_id !== 'undefined') {
    try {
      run_id = decodeURIComponent(run_id);
    } catch (e) {
      console.warn('Failed to decode run_id:', run_id);
    }
  }
  
  console.log('🔍 FINAL PARAMS DEBUG:', {
    useParams_workflow: params.workflow_id,
    useParams_run: params.run_id,
    final_workflow_id: workflow_id,
    final_run_id: run_id,
    isClient,
    clientUrlParams
  });

  const [workflowData, setWorkflowData] = useState<WorkflowResult | null>(null)
  const [assistantOrder, setAssistantOrder] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isTerminating, setIsTerminating] = useState(false)
  const [expandedAssistants, setExpandedAssistants] = useState<Set<number>>(new Set())
  const [isPolling, setIsPolling] = useState(true)
  const [outputModal, setOutputModal] = useState<{isOpen: boolean, output: any, stageName: string}>({
    isOpen: false,
    output: null,
    stageName: ''
  })
  
  const pollingRef = useRef<NodeJS.Timeout | null>(null)

  const showOutputModal = (output: any, stageName: string) => {
    setOutputModal({
      isOpen: true,
      output,
      stageName
    });
  };

  const closeOutputModal = () => {
    setOutputModal({
      isOpen: false,
      output: null,
      stageName: ''
    });
  };

  // Načtení pořadí asistentů z workflow dat
  const extractAssistantOrder = (stageLogsData: any[]) => {
    if (!stageLogsData || stageLogsData.length === 0) {
      return [];
    }
    
    // Extrahování stage names a seřazení podle timestampu (chronologické pořadí)
    const assistantNames = stageLogsData
      .filter(log => log.stage && log.stage !== 'load_assistants_config' && log.stage !== 'save_pipeline_result') // Filtrujeme konfigurační fázi a interní operace
      .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0)) // Seřazení chronologicky
      .map(log => log.stage);
      
    // Odstranění duplicit ale zachování pořadí
    const uniqueOrder = [...new Set(assistantNames)];
    
    console.log('🔄 Extrahováno pořadí asistentů z workflow:', uniqueOrder);
    return uniqueOrder;
  };

  // PublishScript specific functions

  const retryPublishScript = async (stageName: string) => {
    try {
      setIsTerminating(true);
      
      // API call to retry only PublishScript  
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/api/retry-publish-script`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow_id: workflow_id,
          run_id: run_id,
          stage: stageName
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('✅ PublishScript retry initiated:', result);
      
      // Restart polling to track progress
      setIsPolling(true);
      
      // ✅ PŘIDÁNO - okamžitě refresh dat po regeneraci
      await fetchWorkflowResult();
      
      alert('🔧 PublishScript byl spuštěn znovu. Sledujte progress...');
    } catch (error) {
      console.error('❌ Error retrying PublishScript:', error);
      alert('Chyba při opakování PublishScript');
    } finally {
      setIsTerminating(false);
    }
  };

  const fetchWorkflowResult = async () => {
    try {
      // Validate IDs before API call
      if (!workflow_id || !run_id || workflow_id === 'undefined' || run_id === 'undefined') {
        console.error('❌ CRITICAL: Invalid workflow/run IDs:', {
          workflow_id,
          run_id,
          type_workflow: typeof workflow_id,
          type_run: typeof run_id
        });
        setError(`Neplatné parametry: workflow_id="${workflow_id}", run_id="${run_id}"`);
        setLoading(false);
        return;
      }
      
      // Debug logging
      console.log('🔍 Debug - Fetching workflow:', {
        useParams_workflow_id: params.workflow_id,
        useParams_run_id: params.run_id,
        final_workflow_id: workflow_id,
        final_run_id: run_id
      })
      
      // URL encode the parameters for the API call
      const encodedWorkflowId = encodeURIComponent(workflow_id)
      const encodedRunId = encodeURIComponent(run_id)
      
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      if (!apiBaseUrl) {
        console.error('❌ CRITICAL: NEXT_PUBLIC_API_BASE_URL není nastaveno!');
        setError('Systémová chyba: API URL není nakonfigurováno');
        setLoading(false);
        return;
      }
      console.log('✅ Using API Base URL:', apiBaseUrl);
      const apiUrl = `${apiBaseUrl}/api/workflow-result/${encodedWorkflowId}/${encodedRunId}`
      console.log('🌐 API URL:', apiUrl)
      
      const response = await fetch(apiUrl)
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Workflow není dokončen nebo výstup není k dispozici')
        } else if (response.status === 500) {
          throw new Error('Nastala chyba při načítání výstupu')
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      }
      
      const data: WorkflowResult = await response.json()
      console.log('✅ Data loaded:', data)
      setWorkflowData(data)
      
      // Extrakce pořadí asistentů z stage logs
      if (data.stage_logs) {
        const order = extractAssistantOrder(data.stage_logs);
        setAssistantOrder(order);
      }
      
      setError(null)
      
      // Stop polling if workflow is finished
      if (data.status !== 'RUNNING' && data.status !== 'STARTED') {
        setIsPolling(false)
      }
    } catch (err) {
      console.error('❌ Error loading workflow:', err)
      setError(err instanceof Error ? err.message : 'Neznámá chyba')
      setIsPolling(false)
    } finally {
      setLoading(false)
    }
  }

  // Setup polling - wait for client-side initialization
  useEffect(() => {
    if (isClient && workflow_id && run_id && workflow_id !== 'undefined' && run_id !== 'undefined') {
      console.log('🚀 Client ready, starting data fetch with:', { workflow_id, run_id });
      fetchWorkflowResult()
    }
  }, [workflow_id, run_id, isClient, clientUrlParams])

  useEffect(() => {
    if (isPolling && workflowData?.status === 'RUNNING') {
      pollingRef.current = setInterval(() => {
        fetchWorkflowResult()
      }, 5000) // Poll every 5 seconds
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [isPolling, workflowData?.status])

  const toggleAssistantExpand = (index: number) => {
    const newExpanded = new Set(expandedAssistants)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedAssistants(newExpanded)
  }

  const terminateWorkflow = async () => {
    if (!confirm('Opravdu chcete ukončit tento workflow? Tato akce je nevratná.')) {
      return
    }

    setIsTerminating(true)
    try {
      // URL encode the parameters for the API call
      const encodedWorkflowId = encodeURIComponent(workflow_id)
      const encodedRunId = encodeURIComponent(run_id)
      
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/workflow-terminate/${encodedWorkflowId}/${encodedRunId}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            reason: 'Long-running workflow terminated by user'
          })
        }
      )
      
      if (response.ok) {
        alert('Workflow byl úspěšně ukončen')
        await fetchWorkflowResult()
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail?.message || 'Chyba při ukončování workflow')
      }
    } catch (err) {
      alert(`Chyba při ukončování: ${err instanceof Error ? err.message : 'Neznámá chyba'}`)
    } finally {
      setIsTerminating(false)
    }
  }

  const getStatusEmoji = (status: string, isWarning: boolean = false): string => {
    if (isWarning && status === 'RUNNING') return '🟠'
    switch (status) {
      case 'RUNNING': return '🟢'
      case 'COMPLETED': return '✅'
      case 'FAILED': return '❌'
      case 'TERMINATED': return '🛑'
      case 'TIMED_OUT': return '⏰'
      default: return '⚠️'
    }
  }

  const formatDateTime = (isoString: string): string => {
    return new Date(isoString).toLocaleString('cs-CZ', {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    
    if (minutes > 0) {
      return `${minutes} min ${remainingSeconds} s`
    }
    return `${remainingSeconds} s`
  }

  const downloadJSON = () => {
    // 🎯 OPRAVA: Stahujeme jen finální článek z PUBLISH asistenta, ne celé workflow
    const publishStage = workflowData?.stage_logs?.find(log => 
      log.stage === 'PublishAssistant' && log.status === 'COMPLETED'
    );
    
    if (publishStage?.output) {
      try {
        // Pokusíme se parsovat output jako JSON
        const publishOutput = typeof publishStage.output === 'string' 
          ? JSON.parse(publishStage.output) 
          : publishStage.output;
          
        const blob = new Blob([JSON.stringify(publishOutput, null, 2)], {
        type: 'application/json'
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
        a.download = `published-article-${workflow_id}-${run_id}.json`
        a.click()
        URL.revokeObjectURL(url)
        
      } catch (e) {
        // Fallback: stáhneme raw output jako text
        const blob = new Blob([publishStage.output], {
          type: 'application/json'
        })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `published-article-${workflow_id}-${run_id}.json`
      a.click()
      URL.revokeObjectURL(url)
      }
    } else {
      alert('Finální článek není k dispozici - workflow možná ještě není dokončen.')
    }
  }

  const showAllAssistantOutputs = () => {
    if (!workflowData?.stage_logs) return;

    // Helper function to clean problematic characters
    const cleanText = (text: string) => {
      return text
        .replace(/[\u{1F300}-\u{1F9FF}]/gu, '') // Remove emojis
        .replace(/[\u{2600}-\u{26FF}]/gu, '') // Remove misc symbols
        .replace(/[\u{2700}-\u{27BF}]/gu, '') // Remove dingbats
        .replace(/[\u{1F100}-\u{1F1FF}]/gu, '') // Remove enclosed alphanumeric supplement
        .replace(/\r\n/g, '\n') // Normalize line endings
        .replace(/\r/g, '\n')
        .trim();
    };

    // Helper function to format output safely
    const formatOutput = (output: any) => {
      if (!output) return '(žádný output)';
      
      if (typeof output === 'string') {
        return cleanText(output);
      } else {
        try {
          return JSON.stringify(output, null, 2);
        } catch (e) {
          return `(chyba při formatování: ${e})`;
        }
      }
    };

    // Helper function to format assistant name
    const formatAssistantName = (stageName: string) => {
      return stageName
        .replace('Assistant', '')
        .replace('_assistant', '')
        .replace('_', ' ')
        .toUpperCase();
    };

    console.log('🔍 Dostupné stage názvy:', workflowData.stage_logs.map(log => log.stage));

    // 🔧 OPRAVA: Používáme CHRONOLOGICKÉ POŘADÍ podle timestamp (stejné jako pipeline)
    // Místo hardcoded mappings řadíme podle skutečného pořadí spuštění

    // Nejdřív seskupíme záznamy podle stage názvu a vezmeme jen nejnovější pro každý stage
    const stageGroups = workflowData.stage_logs
      .filter(log => log.stage && log.stage !== 'load_assistants_config' && log.stage !== 'save_pipeline_result')
      .reduce((groups, log) => {
        const stageName = log.stage;
        if (!groups[stageName] || log.timestamp > groups[stageName].timestamp) {
          groups[stageName] = log;
        }
        return groups;
      }, {});

    // Převedeme na array a seřadíme chronologicky podle původního timestamp (ne nejnovějšího)
    const allStages = Object.values(stageGroups)
      .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));

    // Filtrujeme jen dokončené pro hlavní sekci a omezujeme na prvních 8
    const assistantStages = allStages.filter(log => log.status === 'COMPLETED').slice(0, 8);

    let combinedOutput = `# KOMPLETNÍ OUTPUTY ASISTENTŮ 1-8\n`;
    combinedOutput += `Workflow: ${workflow_id}\n`;
    combinedOutput += `Run ID: ${run_id}\n`;
    combinedOutput += `Čas: ${new Date().toLocaleString('cs-CZ')}\n`;
    combinedOutput += `Pořadí: CHRONOLOGICKÉ (podle skutečného spuštění v pipeline)\n\n`;
    combinedOutput += `${'='.repeat(80)}\n\n`;

    assistantStages.forEach((stage, index) => {
      combinedOutput += `## ${index + 1}. ${formatAssistantName(stage.stage)}\n`;
        combinedOutput += `Status: ✅ DOKONČENO\n`;
        combinedOutput += `Stage název: ${stage.stage}\n`;
      
        if (stage.duration) {
          combinedOutput += `Doba trvání: ${stage.duration.toFixed(1)}s\n`;
        }
      
      combinedOutput += `Čas spuštění: ${new Date(stage.timestamp * 1000).toLocaleString('cs-CZ')}\n`;
      combinedOutput += `Chronologické pořadí: #${index + 1}\n\n`;
        
        combinedOutput += `### VÝSTUP:\n`;
        combinedOutput += formatOutput(stage.output);
      
      combinedOutput += `\n\n${'-'.repeat(60)}\n\n`;
    });

    // Nedokončené asistenti - jen ti, kteří skutečně nejsou dokončení
    const incompleteStages = allStages.filter(log => log.status !== 'COMPLETED');

    if (incompleteStages.length > 0) {
      combinedOutput += `# NEDOKONČENÉ ASISTENTI\n\n`;
      incompleteStages.forEach((stage, index) => {
        combinedOutput += `## ${formatAssistantName(stage.stage)}\n`;
        combinedOutput += `Status: ❌ ${stage.status}\n`;
        combinedOutput += `Stage název: ${stage.stage}\n`;
        if (stage.error) {
          combinedOutput += `Chyba: ${stage.error}\n`;
        }
        combinedOutput += `\n${'-'.repeat(40)}\n\n`;
      });
    }

    // Clean the entire output before showing
    const cleanedOutput = cleanText(combinedOutput);
    
    // Show modal with the combined output
    showOutputModal(cleanedOutput, `Kompletní outputy asistentů 1-${assistantStages.length} (chronologické pořadí)`);
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span>Načítám detail workflow...</span>
        </div>
        <div className="mt-4 p-4 bg-gray-100 text-sm">
          <h3>🔍 DEBUG INFO:</h3>
          <p><strong>NEXT_PUBLIC_API_BASE_URL:</strong> {process.env.NEXT_PUBLIC_API_BASE_URL || 'UNDEFINED'}</p>
          <p><strong>useParams() workflow_id:</strong> {params.workflow_id as string || 'undefined'}</p>
          <p><strong>useParams() run_id:</strong> {params.run_id as string || 'undefined'}</p>
          <p><strong>Client URL workflow_id:</strong> {clientUrlParams.workflow_id || 'null'}</p>
          <p><strong>Client URL run_id:</strong> {clientUrlParams.run_id || 'null'}</p>
          <p><strong>Final workflow_id:</strong> {workflow_id}</p>
          <p><strong>Final run_id:</strong> {run_id}</p>
          <p><strong>Is client:</strong> {isClient ? 'true' : 'false'}</p>
          {isClient && (
            <p><strong>Window path:</strong> {window.location.pathname}</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <Link href="/workflows" className="text-blue-600 hover:underline">
          ← Zpět na workflows
        </Link>
      </div>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Detail Workflow</h1>
        {isPolling && workflowData?.status === 'RUNNING' && (
          <div className="flex items-center gap-2 text-green-600">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">Auto-refresh každých 5s</span>
          </div>
        )}
      </div>

      <div className="bg-white border border-gray-300 rounded-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Workflow ID
            </label>
            <div className="px-3 py-2 bg-gray-100 border rounded font-mono text-sm">
              {workflow_id}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Run ID
            </label>
            <div className="px-3 py-2 bg-gray-100 border rounded font-mono text-sm">
              {run_id}
            </div>
          </div>
        </div>

        {error ? (
          <div className="p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        ) : workflowData ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-xl" title={workflowData.warning ? "Běh trvá déle než obvykle" : ""}>
                    {getStatusEmoji(workflowData.status, workflowData.warning)}
                  </span>
                  <span className="font-medium">{workflowData.status}</span>
                  {workflowData.warning && (
                    <span className="text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
                      Long-running
                    </span>
                  )}
                </div>
              </div>
              {workflowData.start_time && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Start
                  </label>
                  <div className="text-sm">
                    {formatDateTime(workflowData.start_time)}
                  </div>
                </div>
              )}
              {workflowData.end_time && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    End
                  </label>
                  <div className="text-sm">
                    {formatDateTime(workflowData.end_time)}
                  </div>
                </div>
              )}
            </div>

            {/* Terminate tlačítko pro long-running RUNNING workflow */}
            {workflowData.status === 'RUNNING' && workflowData.warning && (
              <div className="mb-6 p-4 bg-orange-50 border border-orange-200 rounded">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-orange-800 mb-1">
                      ⚠️ Dlouhodobě běžící workflow
                    </h3>
                    <p className="text-sm text-orange-700">
                      Tento workflow běží neobvykle dlouho a může být uvíznutý. Můžete ho ručně ukončit.
                    </p>
                  </div>
                  <button
                    onClick={terminateWorkflow}
                    disabled={isTerminating}
                    className={`px-4 py-2 rounded font-medium ${
                      isTerminating 
                        ? 'bg-gray-400 text-gray-200 cursor-not-allowed' 
                        : 'bg-red-600 hover:bg-red-700 text-white'
                    }`}
                  >
                    {isTerminating ? 'Ukončuji...' : '🛑 Ukončit workflow'}
                  </button>
                </div>
              </div>
            )}

            {/* Aktuální fáze pro RUNNING workflow */}
            {workflowData.status === 'RUNNING' && workflowData.current_phase && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded">
                <h3 className="text-lg font-semibold mb-2">🔄 Aktuální stav</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Aktuální fáze
                    </label>
                    <div className="text-base font-medium">
                      {workflowData.current_phase}
                    </div>
                  </div>
                  {workflowData.elapsed_seconds && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Celková doba běhu
                      </label>
                      <div className="text-base">
                        {formatDuration(workflowData.elapsed_seconds)}
                      </div>
                    </div>
                  )}
                  {workflowData.activity_elapsed_seconds !== undefined && workflowData.activity_elapsed_seconds > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Doba v aktuální fázi
                      </label>
                      <div className="text-base">
                        {formatDuration(workflowData.activity_elapsed_seconds)}
                        {workflowData.activity_attempt && workflowData.activity_attempt > 1 && (
                          <span className="text-xs text-gray-600 ml-2">
                            (pokus {workflowData.activity_attempt})
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
                {workflowData.diagnostic_error && (
                  <div className="mt-2 text-xs text-orange-600">
                    Diagnostika: {workflowData.diagnostic_error}
                  </div>
                )}
              </div>
            )}

            {/* Enhanced Pipeline Progress Component */}
            {workflowData.stage_logs && workflowData.stage_logs.length > 0 && (
              <PipelineProgress
                stages={(() => {
                  // PŮVODNÍ LOGIKA - zobrazit workflow logy + deduplikovat PublishScript
                  let originalStages = workflowData.stage_logs.filter(log => 
                    log.stage && 
                    log.stage !== 'load_assistants_config' && 
                    log.stage !== 'save_pipeline_result'
                  );
                  
                  // 🔧 OPRAVA: Deduplikovat PublishScript - nechat jen poslední (nejnovější)
                  const publishScriptStages = originalStages.filter(stage => 
                    stage.stage === 'PublishScript'
                  );
                  
                  if (publishScriptStages.length > 1) {
                    // Odstraň všechny PublishScript
                    originalStages = originalStages.filter(stage => stage.stage !== 'PublishScript');
                    // Přidej jen poslední (nejnovější) PublishScript
                    const latestPublishScript = publishScriptStages[publishScriptStages.length - 1];
                    originalStages.push(latestPublishScript);
                  }
                  
                  // Přidat PublishScript jako poslední pokud není v logách vůbec
                  const hasPublishScript = originalStages.some(stage => 
                    stage.stage === 'PublishScript' || stage.stage === 'publish_script'
                  );
                  
                  if (!hasPublishScript) {
                    const publishScriptStage = {
                      stage: 'publish_script',
                      status: 'PENDING',
                      timestamp: 0,
                      duration: undefined,
                      error: undefined,
                      output: undefined,
                      assistant_name: 'PublishScript (Deterministický)',
                      assistant_description: '🔧 DETERMINISTICKÝ SCRIPT - už není AI! Převádí pipeline data na HTML/JSON export bez LLM volání.'
                    };
                    
                    originalStages.push(publishScriptStage);
                  }
                  
                  console.log('🔧 Pipeline stages s PublishScript:', originalStages);
                  return originalStages;
                })()}
                assistantOrder={assistantOrder}
                expandedAssistants={expandedAssistants}
                toggleAssistantExpand={toggleAssistantExpand}
                showOutputModal={showOutputModal}
                retryPublishScript={retryPublishScript}
              />
            )}

            {workflowData.result && (
              <>
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-semibold">📄 Finální JSON Výstup</h2>
                  <div className="flex gap-2">
                    <button
                      onClick={showAllAssistantOutputs}
                      className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                      title="Zobrazí outputy všech asistentů 1-8 v okně pro prohlížení a kopírování"
                    >
                      📋 Zobrazit výstupy 1-8
                    </button>
                    <button
                      onClick={downloadJSON}
                      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      📥 Stáhnout JSON
                    </button>
                  </div>
                </div>
                <pre className="bg-gray-100 border rounded p-4 text-sm overflow-auto max-h-96">
                  {(() => {
                    // 🎯 OPRAVA: Zobrazujeme jen finální článek z PUBLISH asistenta, ne celé workflow
                    const publishStage = workflowData.stage_logs?.find(log => 
                      log.stage === 'PublishAssistant' && log.status === 'COMPLETED'
                    );
                    
                    if (publishStage?.output) {
                      try {
                        // Pokusíme se parsovat output jako JSON
                        const publishOutput = typeof publishStage.output === 'string' 
                          ? JSON.parse(publishStage.output) 
                          : publishStage.output;
                        return JSON.stringify(publishOutput, null, 2);
                      } catch (e) {
                        // Pokud se nepodaří parsovat, zobrazíme raw output
                        return publishStage.output;
                      }
                    }
                    
                    // Fallback: pokud není PublishAssistant dostupný
                    return "Finální výstup není k dispozici - workflow možná ještě není dokončen.";
                  })()}
                </pre>
              </>
            )}
          </>
        ) : null}
      </div>

      {/* Output Modal */}
      <OutputModal
        isOpen={outputModal.isOpen}
        onClose={closeOutputModal}
        output={outputModal.output}
        stageName={outputModal.stageName}
      />
    </div>
  )
} 