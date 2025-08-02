'use client';

import React, { useState } from 'react';
import { 
  getAssistantBySlug, 
  getAssistantIcon, 
  getAssistantColor,
  getAssistantBgColor,
  type AssistantConfig 
} from '../constants/assistantList';
import ImageGallery from './ImageGallery';

interface StageLog {
  stage: string;
  status: string;
  timestamp: number;
  duration?: number;
  error?: string;
  output?: any;
  metadata?: any;
  order?: number;
  function_key?: string;
}

interface AssistantRendererProps {
  stages: StageLog[];
  assistants?: AssistantConfig[]; // Dynamicky načtení asistenti místo FINAL_ASSISTANTS
  onStageClick?: (stage: StageLog) => void;
  showProgress?: boolean;
  showEstimatedTime?: boolean;
}

interface AssistantCardProps {
  stage: StageLog;
  assistant: AssistantConfig;
  index: number;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onStageClick?: (stage: StageLog) => void;
}

/**
 * Komponenta pro zobrazení jednotlivého asistenta v pipeline
 */
const AssistantCard: React.FC<AssistantCardProps> = ({
  stage,
  assistant,
  index,
  isExpanded,
  onToggleExpand,
  onStageClick
}) => {
  const getStatusIcon = (status: string) => {
    switch (status.toUpperCase()) {
      case 'COMPLETED': return '✅';
      case 'FAILED': return '❌';
      case 'STARTED':
      case 'RUNNING': return '🔄';
      case 'TIMED_OUT': return '⏰';
      default: return '⚠️';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case 'COMPLETED': return 'bg-green-50 border-green-200 text-green-800';
      case 'FAILED': return 'bg-red-50 border-red-200 text-red-800';
      case 'STARTED':
      case 'RUNNING': return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'TIMED_OUT': return 'bg-orange-50 border-orange-200 text-orange-800';
      default: return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '--';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const parseImageOutput = (output: any): { images: any[], hasImages: boolean } => {
    if (!output) return { images: [], hasImages: false };
    
    try {
      let parsedOutput = output;
      
      if (typeof output === 'string') {
        parsedOutput = JSON.parse(output);
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

  return (
    <div className={`border rounded-xl transition-all duration-200 hover:shadow-md 
      ${getStatusColor(stage.status)} ${isExpanded ? 'shadow-lg' : ''}`}>
      
      {/* Header */}
      <div 
        className="p-4 cursor-pointer flex items-center justify-between"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-4">
          {/* Order number */}
          <div className={`w-8 h-8 rounded-full ${assistant.bgColor} ${assistant.color} 
            flex items-center justify-center font-bold text-sm`}>
            {assistant.order}
          </div>
          
          {/* Assistant info */}
          <div className="flex items-center gap-3">
            <span className="text-2xl">{assistant.icon}</span>
            <div>
              <h4 className="font-semibold text-gray-900">{assistant.name}</h4>
              <p className="text-sm text-gray-600">{assistant.description}</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Status */}
          <div className="flex items-center gap-2">
            <span className="text-lg">{getStatusIcon(stage.status)}</span>
            <span className="font-medium text-sm">{stage.status}</span>
          </div>
          
          {/* Duration */}
          {stage.duration && (
            <div className="text-sm text-gray-500">
              {formatDuration(stage.duration)}
            </div>
          )}
          
          {/* Expand/Collapse icon */}
          <div className="text-gray-400">
            {isExpanded ? '▼' : '▶'}
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-200">
          <div className="pt-4 space-y-4">
            
            {/* Assistant metadata */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-600">API Type:</span>
                <div className="font-mono">{assistant.apiType}</div>
              </div>
              <div>
                <span className="font-medium text-gray-600">Model:</span>
                <div className="font-mono">{assistant.model}</div>
              </div>
              <div>
                <span className="font-medium text-gray-600">Input:</span>
                <div>{assistant.inputType}</div>
              </div>
              <div>
                <span className="font-medium text-gray-600">Output:</span>
                <div>{assistant.outputType}</div>
              </div>
            </div>

            {/* Error message */}
            {stage.error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <h5 className="font-semibold text-red-800 mb-1">❌ Chyba:</h5>
                <p className="text-red-700 text-sm">{stage.error}</p>
              </div>
            )}

            {/* Output content */}
            {stage.output && stage.status === 'COMPLETED' && (
              <div className="space-y-3">
                <h5 className="font-semibold text-gray-900">📤 Výstup:</h5>
                
                {/* Special handling for ImageRendererAssistant */}
                {assistant.apiType === 'DALLE' && (() => {
                  const { images, hasImages } = parseImageOutput(stage.output);
                  if (hasImages) {
                    return (
                      <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4">
                        <ImageGallery images={images} title="🎨 Vygenerované obrázky" />
                      </div>
                    );
                  }
                })()}
                
                {/* JSON output */}
                <div className="bg-gray-50 rounded-lg p-3 max-h-64 overflow-y-auto">
                  <pre className="text-xs whitespace-pre-wrap break-words">
                    {typeof stage.output === 'string' 
                      ? stage.output 
                      : JSON.stringify(stage.output, null, 2)}
                  </pre>
                </div>
                
                {/* Action buttons */}
                <div className="flex gap-2">
                  {onStageClick && (
                    <button
                      onClick={() => onStageClick(stage)}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                    >
                      🔍 Detail
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Hlavní komponenta pro zobrazení všech 10 asistentů v pipeline
 */
const AssistantRenderer: React.FC<AssistantRendererProps> = ({
  stages,
  assistants = [], // Fallback na prázdný array pokud nejsou předáni
  onStageClick,
  showProgress = true,
  showEstimatedTime = true
}) => {
  const [expandedAssistants, setExpandedAssistants] = useState<Set<number>>(new Set());

  const toggleAssistantExpand = (index: number) => {
    const newExpanded = new Set(expandedAssistants);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedAssistants(newExpanded);
  };

  // Seřazení stages podle pořadí asistentů z props nebo podle timestampu
  const sortedStages = [...stages].sort((a, b) => {
    const assistantA = getAssistantBySlug(a.stage) || assistants.find(ast => ast.name === a.stage);
    const assistantB = getAssistantBySlug(b.stage) || assistants.find(ast => ast.name === b.stage);
    
    const orderA = assistantA?.order || a.timestamp || 999;
    const orderB = assistantB?.order || b.timestamp || 999;
    
    return orderA - orderB;
  });

  // Statistiky
  const completedCount = sortedStages.filter(s => s.status === 'COMPLETED').length;
  const failedCount = sortedStages.filter(s => s.status === 'FAILED' || s.status === 'TIMED_OUT').length;
  const runningCount = sortedStages.filter(s => s.status === 'RUNNING' || s.status === 'STARTED').length;

  const totalDuration = sortedStages.reduce((sum, stage) => sum + (stage.duration || 0), 0);
  const estimatedTotalTime = assistants.reduce((sum, assistant) => sum + (assistant.estimatedDuration || 60), 0);

  return (
    <div className="space-y-6">
      
      {/* Header with progress */}
      {showProgress && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-2xl font-bold text-gray-900">🤖 Pipeline asistentů (10)</h3>
            <div className="text-right">
              <div className="text-2xl font-bold text-gray-900">
                {completedCount}/{assistants.length || sortedStages.length}
              </div>
              <div className="text-sm text-gray-500">dokončeno</div>
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
            <div 
              className="bg-gradient-to-r from-blue-500 to-green-500 h-4 rounded-full transition-all duration-700"
              style={{ width: `${(completedCount / (assistants.length || sortedStages.length || 1)) * 100}%` }}
            />
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="bg-green-50 rounded-lg p-3">
              <div className="font-bold text-green-600">{completedCount}</div>
              <div className="text-green-800">✅ Dokončeno</div>
            </div>
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="font-bold text-blue-600">{runningCount}</div>
              <div className="text-blue-800">🔄 Běží</div>
            </div>
            <div className="bg-red-50 rounded-lg p-3">
              <div className="font-bold text-red-600">{failedCount}</div>
              <div className="text-red-800">❌ Selhalo</div>
            </div>
            {showEstimatedTime && (
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="font-bold text-gray-600">
                  {Math.round(totalDuration)}s / {estimatedTotalTime}s
                </div>
                <div className="text-gray-800">⏱ Čas</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Assistant cards */}
      <div className="space-y-4">
        {(assistants.length > 0 ? assistants : sortedStages.map((stage, idx) => ({
          id: stage.stage, name: stage.stage, slug: stage.stage, order: idx + 1,
          icon: "🤖", color: "text-gray-600", bgColor: "bg-gray-50",
          description: `Assistant ${stage.stage}`, inputType: "string", outputType: "string",
          apiType: "GPT" as const, model: "gpt-4o", estimatedDuration: 60
        }))).map((assistant, index) => {
          // Najdi odpovídající stage pro tohoto asistenta
          const stage = sortedStages.find(s => 
            s.stage === assistant.name || 
            s.stage === assistant.slug ||
            s.function_key === assistant.slug
          );

          // Pokud stage neexistuje, vytvoř placeholder
          const stageToRender = stage || {
            stage: assistant.name,
            status: 'PENDING',
            timestamp: Date.now() / 1000,
            order: assistant.order
          };

          return (
            <AssistantCard
              key={assistant.id}
              stage={stageToRender}
              assistant={assistant}
              index={index}
              isExpanded={expandedAssistants.has(index)}
              onToggleExpand={() => toggleAssistantExpand(index)}
              onStageClick={onStageClick}
            />
          );
        })}
      </div>

      {/* Empty state */}
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

export default AssistantRenderer;