'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface WorkflowRun {
  id: string              // Temporal: run_id
  workflow_id: string     // Temporal: workflow_id
  run_id: string          // Temporal: run_id (duplicated)
  topic: string           // Temporal: extracted from workflow_id
  projectName: string     // Temporal: "Neznámý projekt" (fallback)
  status: string          // Temporal: status name (TIMED_OUT, COMPLETED, etc.)
  workflow_type: string   // Temporal: AssistantPipelineWorkflow, SEOWorkflow
  startedAt: string       // Temporal: start_time ISO string
  finishedAt: string | null // Temporal: end_time ISO string or null
  // Computed fields (optional)
  elapsedSeconds?: number | null
  stageCount?: number | null
  totalStages?: number | null
}

interface WorkflowRunsResponse {
  workflows?: WorkflowRun[]  // Keep compatibility with old response format
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())

  const fetchWorkflows = async () => {
    console.log('🚀 DEBUG: fetchWorkflows STARTED');
    setError(null)
    
    try {
      console.log('🔍 DEBUG: Načítám workflows z API...');
      console.log('🔗 API BASE URL:', process.env.NEXT_PUBLIC_API_BASE_URL);
      
      // ✅ OPRAVENO: Používáme databázový endpoint místo Temporal serveru
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const apiUrl = `${apiBaseUrl}/api/workflow-runs?limit=50`;
      console.log('🌐 DEBUG: Full API URL:', apiUrl);
      
      const response = await fetch(apiUrl)
      console.log('📡 DEBUG: Response status:', response.status, response.statusText);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      console.log('⚙️ DEBUG: Workflows response:', data);
      
      // ✅ OPRAVENO: Databázový API vrací array přímo
      const workflowsArray = Array.isArray(data) ? data : []
      console.log('📋 DEBUG: Workflows array:', workflowsArray);
      console.log('📋 DEBUG: Array length:', workflowsArray.length);
      
      setWorkflows(workflowsArray)
      console.log('✅ DEBUG: setWorkflows called with:', workflowsArray.length, 'items');
      
    } catch (err) {
      console.error('❌ DEBUG: Error fetching workflows:', err);
      setError(err instanceof Error ? err.message : 'Neznámá chyba')
    } finally {
      console.log('🏁 DEBUG: Setting loading to false');
      setLoading(false)
      console.log('🏁 DEBUG: fetchWorkflows FINISHED');
    }
  }

  const deleteWorkflow = async (runId: string, topic: string) => {
    // ⚠️ DOČASNĚ VYPNUTO: Temporal workflows nelze mazat přes databázové API
    alert('Mazání Temporal workflows zatím není podporováno. Workflows můžete ukončit přes Temporal UI.');
    return;
  }

  useEffect(() => {
    // Počáteční načtení
    fetchWorkflows()

    // Autorefresh každých 10 sekund
    const interval = setInterval(fetchWorkflows, 10000)

    // Cleanup interval při unmount
    return () => clearInterval(interval)
  }, [])

  const getStatusIcon = (status: string, startTime?: string) => {
    switch (status?.toUpperCase()) {
      case 'COMPLETED': return '✅';
      case 'FAILED': return '❌';
      case 'RUNNING': 
        // 🚨 HANGING DETECTION - pokud běží více než 15 minut, označit jako podezřelé
        if (startTime) {
          const startDate = new Date(startTime);
          const now = new Date();
          const diffMinutes = (now.getTime() - startDate.getTime()) / (1000 * 60);
          if (diffMinutes > 15) {
            return '⚠️'; // Podezřelé hanging
          }
        }
        return '🔄';
      case 'CANCELLED': return '🚫';
      case 'TERMINATED': return '🛑';
      case 'TIMED_OUT': return '⏰';
      case 'CONTINUED_AS_NEW': return '🔁';
      default: return '⚠️';
    }
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('cs-CZ', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusText = (status: string, startTime?: string) => {
    if (status?.toUpperCase() === 'RUNNING' && startTime) {
      const startDate = new Date(startTime);
      const now = new Date();
      const diffMinutes = (now.getTime() - startDate.getTime()) / (1000 * 60);
      if (diffMinutes > 15) {
        return `${status} (⚠️ Běží ${Math.round(diffMinutes)} min - možné zaseknutí)`;
      }
      return `${status} (${Math.round(diffMinutes)} min)`;
    }
    return status;
  }

  const truncateHash = (hash: string | undefined) => hash ? hash.substring(0, 8) : 'N/A'

  if (loading && workflows.length === 0) {
    return <div className="p-8">Načítám workflows...</div>
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Workflows</h1>
      
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          Chyba: {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-2 text-left font-medium text-gray-900">Status</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Projekt</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Téma</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Typ</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Workflow ID</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Run ID</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Spuštěno</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Dokončeno</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Akce</th>
              <th className="px-4 py-2 text-left font-medium text-gray-900">Smazat</th>
            </tr>
          </thead>
          <tbody>
            {workflows.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                  Žádné workflows nenalezeny
                </td>
              </tr>
            ) : (
              workflows.map((workflow) => (
                <tr key={`${workflow.workflow_id}-${workflow.run_id}`} className="hover:bg-gray-50">
                  <td className="px-4 py-2 border-b">
                    <span title={getStatusText(workflow.status, workflow.startedAt || workflow.createdAt)}>
                      {getStatusIcon(workflow.status, workflow.startedAt || workflow.createdAt)}
                    </span>
                  </td>
                  <td className="px-4 py-2 border-b">
                    <span className="text-sm text-gray-600" title={workflow.projectName}>
                      {workflow.projectName}
                    </span>
                  </td>
                  <td className="px-4 py-2 border-b">
                    <span className="text-sm text-gray-900" title={workflow.topic}>
                      {workflow.topic?.substring(0, 30)}{workflow.topic?.length > 30 ? '...' : ''}
                    </span>
                  </td>
                  <td className="px-4 py-2 border-b">
                    <span className="text-sm text-gray-600" title={workflow.workflow_type}>
                      {workflow.workflow_type?.replace('Workflow', '')}</span>
                  </td>
                  <td className="px-4 py-2 border-b">
                    <span title={workflow.workflow_id}>
                      {truncateHash(workflow.workflow_id)}
                    </span>
                  </td>
                  <td className="px-4 py-2 border-b">
                    <span title={workflow.run_id}>
                      {truncateHash(workflow.run_id)}
                    </span>
                  </td>
                  <td className="px-4 py-2 border-b">
                    {formatDateTime(workflow.startedAt)}
                  </td>
                  <td className="px-4 py-2 border-b">
                    {workflow.finishedAt ? formatDateTime(workflow.finishedAt) : '–'}
                  </td>
                  <td className="px-4 py-2 border-b">
                    <Link 
                      href={`/workflows/${encodeURIComponent(workflow.workflow_id)}/${encodeURIComponent(workflow.run_id)}`}
                      className="text-blue-600 hover:underline"
                    >
                      Zobrazit
                    </Link>
                  </td>
                  <td className="px-4 py-2 border-b">
                    <button
                      onClick={() => deleteWorkflow(workflow.run_id, workflow.topic)}
                      disabled={deletingIds.has(workflow.run_id)}
                      className="text-red-600 hover:text-red-800 disabled:text-gray-400 disabled:cursor-not-allowed"
                      title="Smazat workflow běh"
                    >
                      {deletingIds.has(workflow.run_id) ? '⏳' : '🗑️'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {workflows.length > 0 && (
        <div className="mt-4 text-sm text-gray-500">
          Zobrazeno {workflows.length} workflows • Autorefresh každých 10s
        </div>
      )}
    </div>
  )
} 