'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

export default function Home() {
  const [recentStats, setRecentStats] = useState({
    projectCount: 0,
    assistantCount: 0,
    workflowCount: 0,
    recentWorkflows: []
  })
  const [projects, setProjects] = useState<any[]>([])
  const [selectedProject, setSelectedProject] = useState('')
  const [topic, setTopic] = useState('')
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isStatsLoading, setIsStatsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Načtení základních statistik
  const fetchStats = async () => {
    try {
      console.log('🔍 DEBUG: Načítám data z API...');
      console.log('🔗 API BASE URL:', process.env.NEXT_PUBLIC_API_BASE_URL);
      
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      console.log('🔗 API BASE URL:', apiBaseUrl);
      
      const projectsResponse = await fetch(`${apiBaseUrl}/api/projects`);
      const projectsData = await projectsResponse.json();
      console.log('📁 DEBUG: Projects data:', projectsData);
      setProjects(projectsData);
      
      // Načtení skutečných workflow z databáze
      const workflowsResponse = await fetch(`${apiBaseUrl}/api/workflow-runs?limit=500`);
      const workflowsData = await workflowsResponse.json();
      console.log('⚙️ DEBUG: Workflows response:', workflowsData);
      console.log('📋 DEBUG: Workflows array:', workflowsData);
      
      const workflowsArray = Array.isArray(workflowsData) ? workflowsData : [];
      
      setRecentStats({
        projectCount: projectsData.length,
        assistantCount: projectsData.reduce((sum: number, p: any) => sum + p.assistantCount, 0),
        workflowCount: workflowsArray.length,
        recentWorkflows: workflowsArray.slice(0, 5)
      });
      
      console.log('✅ DEBUG: Final recentStats:', {
        projectCount: projectsData.length,
        workflowCount: workflowsArray.length,
        recentWorkflows: workflowsArray.slice(0, 5)
      });
    } catch (err) {
      console.error('❌ DEBUG: Error fetching stats:', err);
    } finally {
      setIsStatsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedProject) {
      setMessage('❌ Musíte vybrat projekt')
      return
    }
    
    if (!topic.trim()) {
      setMessage('❌ Zadejte prosím téma')
      return
    }
    
    setIsSubmitting(true)
    setMessage('')
    
    try {
      let csvData = null
      
      // Načtení CSV jako Base64, pokud je nahraný
      if (csvFile) {
        const base64Content = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            const result = reader.result as string
            // Odstranění prefixu "data:text/csv;base64,"
            const base64 = result.split(',')[1]
            resolve(base64)
          }
          reader.onerror = reject
          reader.readAsDataURL(csvFile)
        })
        
        csvData = {
          name: csvFile.name,
          content: base64Content
        }
      }

      const requestData = {
        project_id: selectedProject,
        topic: topic.trim(),
        ...(csvData && { csv: csvData })
      }

      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      
      console.log('🚀 Odesílám požadavek:', {
        url: `${apiBaseUrl}/api/pipeline-run`,
        method: 'POST',
        data: requestData
      })

      const response = await fetch(`${apiBaseUrl}/api/pipeline-run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      })

      console.log('📨 Response status:', response.status)
      
      if (!response.ok) {
        const errorData = await response.text()
        console.error('❌ Response error:', errorData)
        throw new Error(`HTTP ${response.status}: ${errorData}`)
      }

      const result = await response.json()
      console.log('✅ Success result:', result)
      
      setMessage(`✅ Pipeline spuštěna pro: "${topic}". Workflow ID: ${result.workflow_id}`)
      setSelectedProject('')
      setTopic('')
      setCsvFile(null)
      
      // Reset file input
      const fileInput = document.getElementById('csvFile') as HTMLInputElement
      if (fileInput) fileInput.value = ''

    } catch (error: any) {
      console.error('❌ Error details:', error)
      setMessage(`❌ Chyba: ${error.message}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('cs-CZ', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusEmoji = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'COMPLETED': return '✅';
      case 'FAILED': return '❌';
      case 'RUNNING': return '🔄';
      case 'CANCELLED': return '🚫';
      case 'TERMINATED': return '🛑';
      case 'TIMED_OUT': return '⏰';
      case 'CONTINUED_AS_NEW': return '🔁';
      default: return '⚠️';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              SEO Farm Orchestrator
            </h1>
            <p className="text-xl text-gray-600 mb-8">
              AI-powered workflow orchestration pro SEO content generation
            </p>
            
            {/* Quick Stats */}
            {isStatsLoading ? (
              <div className="animate-pulse flex justify-center space-x-4">
                <div className="h-8 w-16 bg-gray-200 rounded"></div>
                <div className="h-8 w-16 bg-gray-200 rounded"></div>
                <div className="h-8 w-16 bg-gray-200 rounded"></div>
              </div>
            ) : recentStats && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <Link href="/projects" className="bg-blue-50 rounded-lg p-3 block">
                  <div className="text-xl font-bold text-blue-600">{recentStats.projectCount}</div>
                  <div className="text-blue-800 font-medium text-sm">📁 Projektů</div>
                </Link>
                <Link href="/projects" className="bg-green-50 rounded-lg p-3 block">
                  <div className="text-xl font-bold text-green-600">{recentStats.assistantCount}</div>
                  <div className="text-green-800 font-medium text-sm">🤖 Asistentů</div>
                </Link>
                <Link href="/workflows" className="bg-purple-50 rounded-lg p-3 block">
                  <div className="text-xl font-bold text-purple-600">{recentStats.workflowCount}</div>
                  <div className="text-purple-800 font-medium text-sm">🏃‍♂️ Workflow běhů</div>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Launch Section */}
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="bg-white rounded-lg border border-gray-200 p-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center">
            🚀 Rychlé spuštění workflow
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="project" className="block text-sm font-medium text-gray-700 mb-2">
                Vyber projekt
              </label>
              <select
                id="project"
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isSubmitting}
              >
                <option value="">-- Vyberte projekt --</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="topic" className="block text-sm font-medium text-gray-700 mb-2">
                Téma pro SEO obsah
              </label>
              <input
                type="text"
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="např. Top 10 AI tools 2025"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label htmlFor="csvFile" className="block text-sm font-medium text-gray-700 mb-2">
                CSV soubor (volitelné)
              </label>
              <input
                type="file"
                id="csvFile"
                accept=".csv"
                onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isSubmitting}
              />
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={isSubmitting || !selectedProject || !topic.trim()}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-3 px-6 rounded-lg transition-colors"
              >
                {isSubmitting ? '⏳ Spouštím...' : '▶️ Spustit SEO pipeline'}
              </button>
            </div>
          </form>

          {message && (
            <div className={`mt-6 p-4 rounded-lg ${message.startsWith('✅') ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <p className={`text-sm ${message.startsWith('✅') ? 'text-green-800' : 'text-red-800'}`}>
                {message}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      {recentStats?.recentWorkflows?.length > 0 && (
        <div className="max-w-6xl mx-auto px-6 pb-12">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold text-gray-900">📊 Poslední aktivita</h3>
              <Link href="/workflows" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                Zobrazit všechny →
              </Link>
            </div>
            
            <div className="space-y-3">
              {recentStats.recentWorkflows.slice(0, 5).map((workflow: any) => (
                <div key={workflow.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{getStatusEmoji(workflow.status)}</span>
                    <div>
                      <div className="font-medium text-gray-900">{workflow.topic}</div>
                      <div className="text-sm text-gray-500">{workflow.projectName}</div>
                    </div>
                  </div>
                  <div className="text-right text-sm text-gray-600">
                    <div className="font-medium">{workflow.status}</div>
                    <div>{formatDate(workflow.startedAt)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
} 