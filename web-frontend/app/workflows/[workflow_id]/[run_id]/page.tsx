'use client'

import { useEffect, useState, useRef } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'

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
}

interface OutputModalProps {
  isOpen: boolean
  onClose: () => void
  output: any
  stageName: string
}

const OutputModal = ({ isOpen, onClose, output, stageName }: OutputModalProps) => {
  if (!isOpen) return null;

  // Function to copy output to clipboard
  const copyOutput = async () => {
    try {
      const textToCopy = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
      await navigator.clipboard.writeText(textToCopy);
      // You could add a toast notification here
      console.log('✅ Výstup zkopírován do clipboardu');
    } catch (err) {
      console.error('❌ Chyba při kopírování:', err);
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

const AssistantCard = ({ stage, index, isExpanded, onToggleExpand, showOutputModal }: AssistantCardProps) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'bg-green-50 border-green-200 shadow-sm'
      case 'FAILED': return 'bg-red-50 border-red-200 shadow-sm'
      case 'STARTED': 
      case 'RUNNING': return 'bg-blue-50 border-blue-200 shadow-sm'
      case 'TIMED_OUT': return 'bg-orange-50 border-orange-200 shadow-sm'
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
      default: return status
    }
  }

  const getProgressColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'bg-green-500'
      case 'FAILED': return 'bg-red-500'
      case 'RUNNING': return 'bg-blue-500'
      case 'TIMED_OUT': return 'bg-orange-500'
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
                {formatAssistantName(stage.stage)}
              </h4>
              <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                <span>
                  {new Date(stage.timestamp * 1000).toLocaleTimeString('cs-CZ')}
                </span>
                {stage.duration && (
                  <span className="flex items-center gap-1">
                    ⏱️ {stage.duration.toFixed(1)}s
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
              'bg-gray-100 text-gray-800'
            }`}>
              {getStatusText(stage.status)}
            </span>

            {/* Output Button */}
            {stage.output && (
              <button
                onClick={() => showOutputModal(stage.output, stage.stage)}
                className="px-3 py-1 bg-blue-600 text-white text-xs rounded-md hover:bg-blue-700 transition-colors"
              >
                📄 Zobrazit výstup
              </button>
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
                    <button 
                      className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                      disabled
                      title="Retry funkcionalita bude implementována později"
                    >
                      🔄 Opakovat (neimplementováno)
                    </button>
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
          {!stage.output && !stage.error && stage.status === 'COMPLETED' && (
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
        </div>
      )}
    </div>
  );
};

const PipelineProgress = ({ stages, assistantOrder, expandedAssistants, toggleAssistantExpand, showOutputModal }: {
  stages: any[]
  assistantOrder: string[]
  expandedAssistants: Set<number>
  toggleAssistantExpand: (index: number) => void
  showOutputModal: (output: any, stageName: string) => void
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
  
  // Decode URL parameters properly to handle special characters
  const workflow_id = decodeURIComponent(params.workflow_id as string)
  const run_id = decodeURIComponent(params.run_id as string)

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
      .filter(log => log.stage && log.stage !== 'load_assistants_config') // Filtrujeme konfigurační fázi
      .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0)) // Seřazení chronologicky
      .map(log => log.stage);
      
    // Odstranění duplicit ale zachování pořadí
    const uniqueOrder = [...new Set(assistantNames)];
    
    console.log('🔄 Extrahováno pořadí asistentů z workflow:', uniqueOrder);
    return uniqueOrder;
  };

  const fetchWorkflowResult = async () => {
    try {
      // Debug logging
      console.log('🔍 Debug - Fetching workflow:', {
        raw_workflow_id: params.workflow_id,
        decoded_workflow_id: workflow_id,
        raw_run_id: params.run_id, 
        decoded_run_id: run_id
      })
      
      // URL encode the parameters for the API call
      const encodedWorkflowId = encodeURIComponent(workflow_id)
      const encodedRunId = encodeURIComponent(run_id)
      
      const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/workflow-result/${encodedWorkflowId}/${encodedRunId}`
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

  // Setup polling
  useEffect(() => {
    if (workflow_id && run_id) {
      fetchWorkflowResult()
    }
  }, [workflow_id, run_id])

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
    if (workflowData?.result) {
      const blob = new Blob([JSON.stringify(workflowData.result, null, 2)], {
        type: 'application/json'
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `seo-output-${workflow_id}-${run_id}.json`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span>Načítám detail workflow...</span>
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
                stages={workflowData.stage_logs}
                assistantOrder={assistantOrder}
                expandedAssistants={expandedAssistants}
                toggleAssistantExpand={toggleAssistantExpand}
                showOutputModal={showOutputModal}
              />
            )}

            {workflowData.result && (
              <>
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-semibold">📄 Finální JSON Výstup</h2>
                  <button
                    onClick={downloadJSON}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    📥 Stáhnout JSON
                  </button>
                </div>
                <pre className="bg-gray-100 border rounded p-4 text-sm overflow-auto max-h-96">
                  {JSON.stringify(workflowData.result, null, 2)}
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