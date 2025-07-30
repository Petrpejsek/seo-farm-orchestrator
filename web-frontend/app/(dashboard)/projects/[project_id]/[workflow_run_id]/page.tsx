'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

interface StageLog {
  stage: string;
  status: string;
  timestamp: number;
  duration?: number;
  error?: string;
}

interface WorkflowResult {
  status: string;
  result?: any;
  resultJson?: any;
  stage_logs?: StageLog[];
  start_time?: string;
  end_time?: string;
  current_phase?: string;
  current_activity_type?: string;
  elapsed_seconds?: number;
  activity_elapsed_seconds?: number;
  activity_attempt?: number;
  is_long_running?: boolean;
  warning?: boolean;
  diagnostic_error?: string;
  failure_details?: {
    message: string;
    type: string;
    stack_trace?: string;
  };
  error?: string;
  details?: string;
  message?: string;
}

interface WorkflowRun {
  id: string;
  projectId: string;
  runId: string;
  workflowId: string;
  topic: string;
  status: string;
  startedAt: string;
  finishedAt?: string;
  outputPath?: string;
  resultJson?: any;
  errorMessage?: string;
  elapsedSeconds?: number;
  stageCount?: number;
  totalStages?: number;
  createdAt: string;
  updatedAt: string;
}

interface StageDetailModal {
  stage: string;
  input: any;
  output: any;
  status: string;
  duration?: number;
  error?: string;
}

export default function WorkflowRunDetailPage() {
  const params = useParams();
  const projectId = params.project_id as string;
  const workflowRunId = params.workflow_run_id as string;

  const [workflowRun, setWorkflowRun] = useState<WorkflowRun | null>(null);
  const [workflowResult, setWorkflowResult] = useState<WorkflowResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isTerminating, setIsTerminating] = useState(false);
  const [selectedStageModal, setSelectedStageModal] = useState<StageDetailModal | null>(null);

  // Načtení workflow run detailu
  const fetchWorkflowRun = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/workflow-run/${workflowRunId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Workflow run nenalezen');
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setWorkflowRun(data);
      
      // Pokud máme workflow/run ID, načteme i Temporal výsledek
      if (data.workflowId && data.runId) {
        fetchWorkflowResult(data.workflowId, data.runId);
      }
    } catch (err) {
      console.error('Error fetching workflow run:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při načítání workflow běhu: ${errorMessage}`);
    }
  };

  // Načtení workflow výsledku z Temporal
  const fetchWorkflowResult = async (workflowId: string, runId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/workflow-result/${workflowId}/${runId}`);
      if (!response.ok) {
        if (response.status === 404) {
          setWorkflowResult({ status: 'NOT_FOUND', message: 'Workflow results not found' });
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setWorkflowResult(data);
    } catch (err) {
      console.error('Error fetching workflow result:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setWorkflowResult({ 
        status: 'ERROR', 
        error: 'Failed to fetch results',
        details: errorMessage
      });
    }
  };

  // Ukončení workflow
  const terminateWorkflow = async () => {
    if (!workflowRun || !window.confirm('Opravdu chcete ukončit tento workflow?')) {
      return;
    }

    try {
      setIsTerminating(true);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/workflow-terminate/${workflowRun.workflowId}/${workflowRun.runId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'Manually terminated from UI' })
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Refresh data
      fetchWorkflowRun();
    } catch (err) {
      console.error('Error terminating workflow:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při ukončování workflow: ${errorMessage}`);
    } finally {
      setIsTerminating(false);
    }
  };

  // Stažení JSON výsledku
  const downloadJSON = () => {
    if (!workflowResult?.result && !workflowRun?.resultJson) {
      return;
    }

    const jsonData = workflowResult?.result || workflowRun?.resultJson;
    const blob = new Blob([JSON.stringify(jsonData, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seo-output-${workflowRun?.workflowId || 'unknown'}-${workflowRun?.runId?.substring(0, 8) || 'unknown'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    fetchWorkflowRun().finally(() => setLoading(false));
  }, [workflowRunId]);

  const getStatusEmoji = (status: string, isWarning: boolean = false): string => {
    if (isWarning && status === 'RUNNING') return '🟠';
    switch (status) {
      case 'RUNNING': return '🟢';
      case 'COMPLETED': return '✅';
      case 'FAILED': return '❌';
      case 'TERMINATED': return '🛑';
      case 'TIMED_OUT': return '⏰';
      default: return '⚠️';
    }
  };

  const getStageStatusEmoji = (status: string): string => {
    switch (status) {
      case 'COMPLETED': return '✅';
      case 'FAILED': return '❌';
      case 'STARTED': return '🔄';
      default: return '⚠️';
    }
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '--';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('cs-CZ', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Helper funkce pro mapování stage names na pipeline ikony
  const getPipelineStageIcon = (stageName: string): string => {
    const stageMap: { [key: string]: string } = {
      'brief_assistant': '📝',
      'generate_llm_friendly_content': '✍️',
      'inject_structured_markup': '🏗️',
      'enrich_with_entities': '🔍',
      'add_conversational_faq': '❓',
      'save_output_to_json': '💾',
      'content_humanizer': '👤',
      'keyword_generator': '🔑',
      'seo': '📈',
      'multimedia': '🎨',
      'qa': '✅',
      'publish': '🚀'
    };
    
    // Zkusím najít přesný match, pak částečný match
    if (stageMap[stageName]) return stageMap[stageName];
    
    for (const [key, icon] of Object.entries(stageMap)) {
      if (stageName.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(stageName.toLowerCase())) {
        return icon;
      }
    }
    
    return '⚙️'; // default icon
  };

  // Helper funkce pro mapování stage names na output data
  const getStageOutputData = (stageName: string, result: any): { input: any; output: any } => {
    if (!result) return { input: null, output: null };
    
    const stageDataMap: { [key: string]: { inputKey?: string; outputKey: string } } = {
      'generate_llm_friendly_content': { outputKey: 'generated' },
      'inject_structured_markup': { inputKey: 'generated', outputKey: 'structured' },
      'enrich_with_entities': { inputKey: 'structured', outputKey: 'enriched' },
      'add_conversational_faq': { inputKey: 'enriched', outputKey: 'faq_final' },
      'save_output_to_json': { inputKey: 'faq_final', outputKey: 'saved_to' }
    };
    
    const mapping = stageDataMap[stageName];
    if (!mapping) {
      return { input: null, output: result[stageName] || null };
    }
    
    return {
      input: mapping.inputKey ? result[mapping.inputKey] : result.topic || null,
      output: result[mapping.outputKey] || null
    };
  };

  // Otevření modal s detaily stage
  const openStageDetail = (log: StageLog) => {
    const { input, output } = getStageOutputData(log.stage, workflowResult?.result);
    
    setSelectedStageModal({
      stage: log.stage,
      input,
      output,
      status: log.status,
      duration: log.duration,
      error: log.error
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Načítám detail workflow...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-800 mb-2">❌ Chyba</h2>
            <p className="text-red-700">{error}</p>
            <div className="mt-4">
              <Link href={`/projects/${projectId}`} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg">
                ← Zpět na projekt
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!workflowRun) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <h2 className="text-xl text-gray-600">Workflow run nenalezen</h2>
            <Link href={`/projects/${projectId}`} className="text-blue-600 hover:underline mt-4 inline-block">
              ← Zpět na projekt
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href="/projects" className="text-blue-600 hover:underline">
                Projekty
              </Link>
              <span className="text-gray-400">/</span>
              <Link href={`/projects/${projectId}`} className="text-blue-600 hover:underline">
                Projekt
              </Link>
              <span className="text-gray-400">/</span>
              <h1 className="text-3xl font-bold text-gray-900">Workflow Detail</h1>
            </div>
            
            <div className="flex items-center gap-4 mb-3">
              <span className="text-2xl">{getStatusEmoji(workflowRun.status, workflowResult?.warning)}</span>
              <h2 className="text-xl font-semibold text-gray-800">{workflowRun.topic}</h2>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                workflowRun.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                workflowRun.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                workflowRun.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {workflowRun.status}
              </span>
              {workflowResult?.warning && (
                <span className="px-3 py-1 rounded-full text-sm font-medium bg-orange-100 text-orange-800">
                  Long-running
                </span>
              )}
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
              <div>
                <span className="font-medium">Workflow ID:</span>
                <div className="font-mono text-xs">{workflowRun.workflowId}</div>
              </div>
              <div>
                <span className="font-medium">Run ID:</span>
                <div className="font-mono text-xs">{workflowRun.runId}</div>
              </div>
              <div>
                <span className="font-medium">Spuštěno:</span>
                <div>{formatDate(workflowRun.startedAt)}</div>
              </div>
              <div>
                <span className="font-medium">Doba běhu:</span>
                <div>{formatDuration(workflowResult?.elapsed_seconds || workflowRun.elapsedSeconds)}</div>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            {(workflowResult?.result || workflowRun.resultJson) && (
              <button
                onClick={downloadJSON}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
              >
                💾 Stáhnout JSON
              </button>
            )}
            
            {workflowRun.status === 'RUNNING' && (
              <button
                onClick={terminateWorkflow}
                disabled={isTerminating}
                className="bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white px-4 py-2 rounded-lg flex items-center gap-2"
              >
                {isTerminating ? '⏳ Ukončuji...' : '🛑 Ukončit workflow'}
              </button>
            )}
          </div>
        </div>

        {/* Current Status for Running Workflow */}
        {workflowRun.status === 'RUNNING' && workflowResult?.current_phase && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              🔄 Aktuální stav
              {workflowResult.warning && (
                <span className="text-sm font-normal text-orange-600">(běží déle než obvykle)</span>
              )}
            </h3>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-600">Aktuální fáze:</span>
                <div className="font-semibold">{workflowResult.current_phase}</div>
              </div>
              <div>
                <span className="font-medium text-gray-600">Celková doba:</span>
                <div>{formatDuration(workflowResult.elapsed_seconds)}</div>
              </div>
              {workflowResult.activity_elapsed_seconds && (
                <div>
                  <span className="font-medium text-gray-600">Doba v fázi:</span>
                  <div>{formatDuration(workflowResult.activity_elapsed_seconds)}</div>
                </div>
              )}
              {workflowResult.activity_attempt && (
                <div>
                  <span className="font-medium text-gray-600">Pokus:</span>
                  <div>#{workflowResult.activity_attempt}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Enhanced Stage Logs */}
        {workflowResult?.stage_logs && workflowResult.stage_logs.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">🔄 Pipeline kroky</h3>
            <div className="space-y-4">
              {workflowResult.stage_logs.map((log, index) => (
                <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border hover:bg-gray-100 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{getPipelineStageIcon(log.stage)}</span>
                      <span className="text-lg">{getStageStatusEmoji(log.status)}</span>
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{log.stage}</div>
                      <div className="text-sm text-gray-500">
                        {new Date(log.timestamp * 1000).toLocaleTimeString('cs-CZ')}
                        {log.duration && ` • ${formatDuration(log.duration)}`}
                      </div>
                      {log.error && (
                        <div className="text-sm text-red-600 mt-1">❌ {log.error}</div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {log.status === 'COMPLETED' && (
                      <button
                        onClick={() => openStageDetail(log)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm flex items-center gap-1"
                      >
                        🔍 Zobrazit výstup
                      </button>
                    )}
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      log.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                      log.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      log.status === 'STARTED' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {log.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stage Detail Modal */}
        {selectedStageModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden">
              <div className="flex justify-between items-center p-6 border-b">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{getPipelineStageIcon(selectedStageModal.stage)}</span>
                  <h3 className="text-xl font-semibold">{selectedStageModal.stage}</h3>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    selectedStageModal.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                    selectedStageModal.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {selectedStageModal.status}
                  </span>
                  {selectedStageModal.duration && (
                    <span className="text-sm text-gray-500">
                      {formatDuration(selectedStageModal.duration)}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setSelectedStageModal(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                {selectedStageModal.error ? (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 className="font-semibold text-red-800 mb-2">❌ Chyba</h4>
                    <p className="text-red-700">{selectedStageModal.error}</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Input */}
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        📥 Vstup
                      </h4>
                      <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                        {selectedStageModal.input ? (
                          <pre className="text-sm whitespace-pre-wrap break-words">
                            {typeof selectedStageModal.input === 'string' 
                              ? selectedStageModal.input 
                              : JSON.stringify(selectedStageModal.input, null, 2)}
                          </pre>
                        ) : (
                          <p className="text-gray-500 italic">Žádný vstup</p>
                        )}
                      </div>
                    </div>
                    
                    {/* Output */}
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        📤 Výstup
                      </h4>
                      <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                        {selectedStageModal.output ? (
                          <pre className="text-sm whitespace-pre-wrap break-words">
                            {typeof selectedStageModal.output === 'string' 
                              ? selectedStageModal.output 
                              : JSON.stringify(selectedStageModal.output, null, 2)}
                          </pre>
                        ) : (
                          <p className="text-gray-500 italic">Žádný výstup</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Final Output Summary */}
        {workflowResult?.result && workflowRun?.status === 'COMPLETED' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              🎯 Shrnutí výstupu
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {workflowResult.result.generated && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="font-medium text-blue-900 mb-2">✍️ Generovaný obsah</div>
                  <div className="text-sm text-blue-700">
                    {workflowResult.result.generated.length} znaků
                  </div>
                </div>
              )}
              
              {workflowResult.result.structured && (
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="font-medium text-green-900 mb-2">🏗️ Strukturovaný markup</div>
                  <div className="text-sm text-green-700">
                    JSON-LD struktura
                  </div>
                </div>
              )}
              
              {workflowResult.result.enriched && (
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="font-medium text-purple-900 mb-2">🔍 Obohacený obsah</div>
                  <div className="text-sm text-purple-700">
                    S entitami a metadaty
                  </div>
                </div>
              )}
              
              {workflowResult.result.faq_final && (
                <div className="bg-orange-50 rounded-lg p-4">
                  <div className="font-medium text-orange-900 mb-2">❓ FAQ sekce</div>
                  <div className="text-sm text-orange-700">
                    Konverzační FAQ
                  </div>
                </div>
              )}
            </div>
            
            {workflowResult.result.saved_to && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-gray-900">💾 Uloženo do:</span>
                    <span className="ml-2 text-sm text-gray-600 font-mono">
                      {workflowResult.result.saved_to}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Failure Details */}
        {workflowResult?.failure_details && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4 text-red-800">❌ Detaily chyby</h3>
            <div className="space-y-3">
              <div>
                <span className="font-medium text-red-700">Zpráva:</span>
                <div className="text-red-600">{workflowResult.failure_details.message}</div>
              </div>
              <div>
                <span className="font-medium text-red-700">Typ:</span>
                <div className="text-red-600">{workflowResult.failure_details.type}</div>
              </div>
              {workflowResult.failure_details.stack_trace && (
                <div>
                  <span className="font-medium text-red-700">Stack trace:</span>
                  <pre className="text-xs text-red-600 bg-red-100 p-3 rounded overflow-x-auto">
                    {workflowResult.failure_details.stack_trace}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* JSON Output */}
        {(workflowResult?.result || workflowRun.resultJson) && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">📄 JSON výstup</h3>
              <button
                onClick={downloadJSON}
                className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
              >
                💾 Stáhnout
              </button>
            </div>
            <pre className="bg-gray-50 p-4 rounded overflow-x-auto text-sm">
              {JSON.stringify(workflowResult?.result || workflowRun.resultJson, null, 2)}
            </pre>
          </div>
        )}

        {/* Diagnostics */}
        {workflowResult && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold mb-4">🔧 Diagnostika</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-600">Temporal status:</span>
                <div>{workflowResult.status}</div>
              </div>
              {workflowResult.start_time && (
                <div>
                  <span className="font-medium text-gray-600">Start time:</span>
                  <div>{formatDate(workflowResult.start_time)}</div>
                </div>
              )}
              {workflowResult.end_time && (
                <div>
                  <span className="font-medium text-gray-600">End time:</span>
                  <div>{formatDate(workflowResult.end_time)}</div>
                </div>
              )}
              {workflowResult.current_activity_type && (
                <div>
                  <span className="font-medium text-gray-600">Current activity:</span>
                  <div className="font-mono text-xs">{workflowResult.current_activity_type}</div>
                </div>
              )}
              {workflowResult.diagnostic_error && (
                <div>
                  <span className="font-medium text-red-600">Diagnostic error:</span>
                  <div className="text-red-600">{workflowResult.diagnostic_error}</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 