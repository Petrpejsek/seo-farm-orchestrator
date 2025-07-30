'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';

interface Assistant {
  id: string;
  name: string;
  functionKey: string;
  inputType: string;
  outputType: string;
  order: number;
  timeout: number;
  heartbeat: number;
  active: boolean;
  description?: string;
  
  // OpenAI parametry
  model: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  system_prompt?: string;
  
  // UX metadata pro admina
  use_case?: string;
  style_description?: string;
  pipeline_stage?: string;
  
  createdAt: string;
  updatedAt: string;
}

interface Project {
  id: string;
  name: string;
  slug: string;
  language: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  assistants: Assistant[];
}

interface WorkflowRun {
  id: string;
  projectId: string;
  projectName: string;
  runId: string;
  workflowId: string;
  topic: string;
  status: string;
  startedAt: string;
  finishedAt?: string;
  elapsedSeconds?: number;
  stageCount?: number;
  totalStages?: number;
}

interface AvailableFunction {
  name: string;
  description: string;
  inputType: string;
  outputType: string;
  defaultTimeout: number;
  defaultHeartbeat: number;
}

interface NewAssistant {
  name: string;
  functionKey: string;
  inputType: string;
  outputType: string;
  order: number;
  timeout: number;
  heartbeat: number;
  active: boolean;
  description: string;
  
  // OpenAI parametry
  model: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  system_prompt: string;
  
  // UX metadata pro admina
  use_case: string;
  style_description: string;
  pipeline_stage: string;
}

interface EditAssistant {
  id: string;
  name: string;
  functionKey: string;
  inputType: string;
  outputType: string;
  order: number;
  timeout: number;
  heartbeat: number;
  active: boolean;
  description: string;
  
  // OpenAI parametry
  model: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  system_prompt: string;
  
  // UX metadata pro admina
  use_case: string;
  style_description: string;
  pipeline_stage: string;
}

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.project_id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [availableFunctions, setAvailableFunctions] = useState<Record<string, AvailableFunction>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'assistants' | 'runs'>('assistants');
  const [showAddAssistant, setShowAddAssistant] = useState(false);
  const [editingAssistant, setEditingAssistant] = useState<EditAssistant | null>(null);
  const [showEditProject, setShowEditProject] = useState(false);
  const [editProjectData, setEditProjectData] = useState({
    name: '',
    language: '',
    description: ''
  });
  const [newAssistant, setNewAssistant] = useState<NewAssistant>({
    name: '',
    functionKey: '',
    inputType: 'string',
    outputType: 'string',
    order: 1,
    timeout: 60,
    heartbeat: 15,
    active: true,
    description: '',
    model: 'gpt-4o',
    temperature: 0.7,
    top_p: 0.9,
    max_tokens: 800,
    system_prompt: '',
    use_case: '',
    style_description: '',
    pipeline_stage: ''
  });

  // Načtení dat projektu
  const fetchProject = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/project/${projectId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Projekt nenalezen');
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setProject(data);
    } catch (err) {
      console.error('Error fetching project:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při načítání projektu: ${errorMessage}`);
    }
  };

  // Načtení workflow běhů
  const fetchWorkflowRuns = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/workflow-runs?project_id=${projectId}&limit=20`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setWorkflowRuns(data);
    } catch (err) {
      console.error('Error fetching workflow runs:', err);
      // Workflow runs selhání není kritické
    }
  };

  // Načtení dostupných funkcí
  const fetchAvailableFunctions = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/assistant-functions`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setAvailableFunctions(data.functions);
    } catch (err) {
      console.error('Error fetching available functions:', err);
    }
  };

  // Smazání asistenta
  const deleteAssistant = async (assistantId: string, assistantName: string) => {
    if (!confirm(`Opravdu chcete smazat asistenta "${assistantName}"?`)) {
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/assistant/${assistantId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Refresh projekt data
      await fetchProject();
      setError('');
    } catch (err) {
      console.error('Error deleting assistant:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při mazání asistenta: ${errorMessage}`);
    }
  };

  // Vytvoření nového asistenta
  const createAssistant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAssistant.name.trim() || !newAssistant.functionKey) return;

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/assistant`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newAssistant,
          projectId: projectId
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      // Reset formuláře a refresh projektu
      setNewAssistant({
        name: '',
        functionKey: '',
        inputType: 'string',
        outputType: 'string',
        order: 1,
        timeout: 60,
        heartbeat: 15,
        active: true,
        description: '',
        model: 'gpt-4o',
        temperature: 0.7,
        top_p: 0.9,
        max_tokens: 800,
        system_prompt: '',
        use_case: '',
        style_description: '',
        pipeline_stage: ''
      });
      setShowAddAssistant(false);
      await fetchProject();
      setError('');
    } catch (err) {
      console.error('Error creating assistant:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při vytváření asistenta: ${errorMessage}`);
    }
  };

  // Úprava existujícího asistenta
  const updateAssistant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAssistant || !editingAssistant.name.trim()) return;

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/assistant/${editingAssistant.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: editingAssistant.name,
          functionKey: editingAssistant.functionKey,
          inputType: editingAssistant.inputType,
          outputType: editingAssistant.outputType,
          order: editingAssistant.order,
          timeout: editingAssistant.timeout,
          heartbeat: editingAssistant.heartbeat,
          active: editingAssistant.active,
          description: editingAssistant.description,
          model: editingAssistant.model,
          temperature: editingAssistant.temperature,
          top_p: editingAssistant.top_p,
          max_tokens: editingAssistant.max_tokens,
          system_prompt: editingAssistant.system_prompt,
          use_case: editingAssistant.use_case,
          style_description: editingAssistant.style_description,
          pipeline_stage: editingAssistant.pipeline_stage
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      // Reset editace a refresh projektu
      setEditingAssistant(null);
      await fetchProject();
      setError('');
    } catch (err) {
      console.error('Error updating assistant:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při úpravě asistenta: ${errorMessage}`);
    }
  };

  // Začátek editace asistenta
  const startEditAssistant = (assistant: Assistant) => {
    setEditingAssistant({
      id: assistant.id,
      name: assistant.name,
      functionKey: assistant.functionKey,
      inputType: assistant.inputType,
      outputType: assistant.outputType,
      order: assistant.order,
      timeout: assistant.timeout,
      heartbeat: assistant.heartbeat,
      active: assistant.active,
      description: assistant.description || '',
      model: assistant.model,
      temperature: assistant.temperature,
      top_p: assistant.top_p,
      max_tokens: assistant.max_tokens,
      system_prompt: assistant.system_prompt || '',
      use_case: assistant.use_case || '',
      style_description: assistant.style_description || '',
      pipeline_stage: assistant.pipeline_stage || ''
    });
  };

  // Editace projektu
  const startEditProject = () => {
    if (project) {
      setEditProjectData({
        name: project.name,
        language: project.language,
        description: project.description || ''
      });
      setShowEditProject(true);
    }
  };

  const updateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!editProjectData.name.trim()) {
      setError('Název projektu je povinný');
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/project/${projectId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: editProjectData.name.trim(),
          language: editProjectData.language.trim() || 'cs',
          description: editProjectData.description.trim() || null
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Zavření modalu a refresh projektu
      setShowEditProject(false);
      await fetchProject();
      setError('');
    } catch (err) {
      console.error('Error updating project:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při úpravě projektu: ${errorMessage}`);
    }
  };

  // Nastavení výchozího pořadí pro nového asistenta
  const getNextOrder = () => {
    if (!project?.assistants || project.assistants.length === 0) return 1;
    return Math.max(...project.assistants.map(a => a.order)) + 1;
  };

  useEffect(() => {
    if (showAddAssistant && project) {
      setNewAssistant(prev => ({ ...prev, order: getNextOrder() }));
    }
  }, [showAddAssistant, project]);

  useEffect(() => {
    Promise.all([
      fetchProject(),
      fetchWorkflowRuns(),
      fetchAvailableFunctions()
    ]).finally(() => {
      setLoading(false);
    });
  }, [projectId]);

  const getStatusEmoji = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '✅';
      case 'FAILED': return '❌';
      case 'RUNNING': return '🟢';
      case 'TERMINATED': return '🛑';
      case 'TIMED_OUT': return '⏰';
      default: return '⚠️';
    }
  };

  const formatDuration = (seconds?: number) => {
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('cs-CZ', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getAssistantStatus = (functionKey: string) => {
    return availableFunctions[functionKey] ? 'EXISTING' : 'MISSING';
  };

  const getAssistantStatusColor = (status: string) => {
    return status === 'EXISTING' ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50';
  };

  const runWorkflow = async (topic: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/pipeline-run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Refresh workflow runs
      fetchWorkflowRuns();
    } catch (err) {
      console.error('Error running workflow:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při spouštění workflow: ${errorMessage}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Načítám projekt...</p>
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
              <Link href="/projects" className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg">
                ← Zpět na projekty
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <h2 className="text-xl text-gray-600">Projekt nenalezen</h2>
            <Link href="/projects" className="text-blue-600 hover:underline mt-4 inline-block">
              ← Zpět na projekty
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
                ← Projekty
              </Link>
              <span className="text-gray-400">/</span>
              <h1 className="text-3xl font-bold text-gray-900">{project.name}</h1>
              <span className="text-2xl">{project.language === 'cs' ? '🇨🇿' : '🇺🇸'}</span>
            </div>
            
            {project.description && (
              <p className="text-gray-600 mb-2">{project.description}</p>
            )}
            
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>📎 <code className="font-mono">{project.slug}</code></span>
              <span>📅 Vytvořeno: {formatDate(project.createdAt)}</span>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => {
                const topic = prompt('Zadejte téma pro workflow:');
                if (topic?.trim()) {
                  runWorkflow(topic.trim());
                }
              }}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              ▶️ Spustit workflow
            </button>
            <button
              onClick={startEditProject}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
            >
              ⚙️ Upravit projekt
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('assistants')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'assistants'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              🤖 Asistenti ({project.assistants.length})
            </button>
            <button
              onClick={() => setActiveTab('runs')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'runs'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              🏃‍♂️ Workflow běhy ({workflowRuns.length})
            </button>
          </nav>
        </div>

        {/* Assistants Tab */}
        {activeTab === 'assistants' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold">🤖 Asistenti</h2>
              <button
                onClick={() => setShowAddAssistant(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
              >
                ➕ Přidat asistenta
              </button>
            </div>

            {/* Formulář pro přidání asistenta */}
            {showAddAssistant && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-semibold mb-4">➕ Nový asistent</h3>
                <form onSubmit={createAssistant} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Název asistenta *
                      </label>
                      <input
                        type="text"
                        value={newAssistant.name}
                        onChange={(e) => setNewAssistant({ ...newAssistant, name: e.target.value })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="např. Content Generator"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Funkce *
                      </label>
                      <select
                        value={newAssistant.functionKey}
                        onChange={(e) => setNewAssistant({ ...newAssistant, functionKey: e.target.value })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <option value="">Vyberte funkci...</option>
                        {Object.entries(availableFunctions).map(([key, func]) => (
                          <option key={key} value={key}>
                            {func.name} ({func.inputType} → {func.outputType})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Pořadí *
                      </label>
                      <input
                        type="number"
                        value={newAssistant.order}
                        onChange={(e) => setNewAssistant({ ...newAssistant, order: parseInt(e.target.value) || 1 })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        min="1"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Timeout (s)
                      </label>
                      <input
                        type="number"
                        value={newAssistant.timeout}
                        onChange={(e) => setNewAssistant({ ...newAssistant, timeout: parseInt(e.target.value) || 60 })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        min="1"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Heartbeat (s)
                      </label>
                      <input
                        type="number"
                        value={newAssistant.heartbeat}
                        onChange={(e) => setNewAssistant({ ...newAssistant, heartbeat: parseInt(e.target.value) || 15 })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        min="1"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Popis
                    </label>
                    <textarea
                      value={newAssistant.description}
                      onChange={(e) => setNewAssistant({ ...newAssistant, description: e.target.value })}
                      className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={2}
                      placeholder="Volitelný popis funkce asistenta..."
                    />
                  </div>

                  {/* OpenAI parametry sekce */}
                  <div className="border-t pt-4 mt-4">
                    <h4 className="text-md font-semibold text-gray-700 mb-2 flex items-center gap-2">
                      🤖 OpenAI parametry
                      <span className="text-sm font-normal text-gray-500">(pouze pro AI funkce)</span>
                    </h4>
                    <p className="text-sm text-gray-600 mb-4 bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
                      💡 <strong>Tyto hodnoty určují chování asistenta při práci s GPT modelem.</strong> 
                      Můžete je přizpůsobit pro kreativní, informativní nebo technické výstupy.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Model *
                        </label>
                        <select
                          value={newAssistant.model}
                          onChange={(e) => setNewAssistant({ ...newAssistant, model: e.target.value })}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          title="Výběr OpenAI modelu - GPT-4o je nejnovější a nejschopnější"
                        >
                          <option value="gpt-4o">GPT-4o (nejnovější)</option>
                          <option value="gpt-4">GPT-4 (robustní)</option>
                          <option value="gpt-3.5-turbo">GPT-3.5 Turbo (rychlý)</option>
                        </select>
                        <p className="text-xs text-gray-500 mt-1">Nejnovější model pro nejlepší výsledky</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Temperature (0.1-2.0) *
                        </label>
                        <input
                          type="number"
                          value={newAssistant.temperature}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value);
                            if (val >= 0.1 && val <= 2.0) {
                              setNewAssistant({ ...newAssistant, temperature: val });
                            }
                          }}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          min="0.1"
                          max="2.0"
                          step="0.1"
                          placeholder="0.7"
                          title="Nižší = přesnější, Vyšší = kreativnější (0.1 až 2.0)"
                        />
                        <p className="text-xs text-gray-500 mt-1">Nižší = přesnější, Vyšší = kreativnější</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Top P (0-1) *
                        </label>
                        <input
                          type="number"
                          value={newAssistant.top_p}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value);
                            if (val >= 0 && val <= 1) {
                              setNewAssistant({ ...newAssistant, top_p: val });
                            }
                          }}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          min="0"
                          max="1"
                          step="0.1"
                          placeholder="0.9"
                          title="Rozsah 0 až 1 – výběr ze širšího spektra odpovědí"
                        />
                        <p className="text-xs text-gray-500 mt-1">Rozsah 0 až 1 – výběr ze širšího spektra odpovědí</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Max tokens (100-4000) *
                        </label>
                        <input
                          type="number"
                          value={newAssistant.max_tokens}
                          onChange={(e) => {
                            const val = parseInt(e.target.value);
                            if (val >= 100 && val <= 4000) {
                              setNewAssistant({ ...newAssistant, max_tokens: val });
                            }
                          }}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          min="100"
                          max="4000"
                          step="100"
                          placeholder="800"
                          title="Maximální délka odpovědi (100 až 4000)"
                        />
                        <p className="text-xs text-gray-500 mt-1">Maximální délka odpovědi</p>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        System prompt (volitelný)
                      </label>
                      <textarea
                        value={newAssistant.system_prompt}
                        onChange={(e) => {
                          if (e.target.value.length <= 10000) {
                            setNewAssistant({ ...newAssistant, system_prompt: e.target.value });
                          }
                        }}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                        placeholder="Např. 'Jsi kreativní SEO expert, který tvoří briefy pro viral obsah...'"
                        maxLength={10000}
                        title="Např. 'Jsi kreativní SEO expert, který tvoří briefy…' (max. 10000 znaků)"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {newAssistant.system_prompt.length}/10000 znaků - Definuje roli a styl asistenta
                      </p>
                    </div>
                  </div>

                  {/* UX metadata sekce */}
                  <div className="border-t pt-4 mt-4">
                    <h4 className="text-md font-semibold text-gray-700 mb-2 flex items-center gap-2">
                      👤 Admin metadata
                      <span className="text-sm font-normal text-gray-500">(popis a kontext)</span>
                    </h4>
                    <p className="text-sm text-gray-600 mb-4 bg-green-50 p-3 rounded-lg border-l-4 border-green-400">
                      📋 <strong>Tyto hodnoty pomáhají adminovi pochopit účel a chování asistenta.</strong> 
                      Zlepšují orientaci při správě orchestrátoru.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Popis asistenta (use case)
                        </label>
                        <input
                          type="text"
                          value={newAssistant.use_case}
                          onChange={(e) => setNewAssistant({ ...newAssistant, use_case: e.target.value })}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="Např. 'Generuje SEO brief pro LLM optimalizaci'"
                          title="Krátké shrnutí, co asistent dělá"
                        />
                        <p className="text-xs text-gray-500 mt-1">Krátké shrnutí, co asistent dělá</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Fáze pipeline *
                        </label>
                        <select
                          value={newAssistant.pipeline_stage}
                          onChange={(e) => setNewAssistant({ ...newAssistant, pipeline_stage: e.target.value })}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          title="Fáze v procesu zpracování"
                        >
                          <option value="">Vyberte fázi...</option>
                          <option value="brief">Brief</option>
                          <option value="research">Research</option>
                          <option value="factvalidation">FactValidation</option>
                          <option value="draft">Draft</option>
                          <option value="humanizer">Humanizer</option>
                          <option value="seo">SEO</option>
                          <option value="multimedia">Multimedia</option>
                          <option value="qa">QA</option>
                          <option value="publish">Publish</option>
                        </select>
                        <p className="text-xs text-gray-500 mt-1">Fáze v workflow pipeline</p>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Styl odpovědi (volitelný)
                      </label>
                      <textarea
                        value={newAssistant.style_description}
                        onChange={(e) => {
                          if (e.target.value.length <= 1000) {
                            setNewAssistant({ ...newAssistant, style_description: e.target.value });
                          }
                        }}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                        placeholder="Např. 'Stručný, přímý styl s důrazem na jednoduchost a čitelnost'"
                        maxLength={1000}
                        title="Popis stylu odpovědí asistenta (max 1000 znaků)"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {newAssistant.style_description.length}/1000 znaků - Jak má asistent odpovídat
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={newAssistant.active}
                        onChange={(e) => setNewAssistant({ ...newAssistant, active: e.target.checked })}
                        className="mr-2"
                      />
                      <span className="text-sm text-gray-700">Aktivní</span>
                    </label>
                  </div>

                  <div className="flex gap-3">
                    <button
                      type="submit"
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
                    >
                      ✅ Vytvořit asistenta
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowAddAssistant(false)}
                      className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-lg"
                    >
                      ❌ Zrušit
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Formulář pro editaci asistenta */}
            {editingAssistant && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-semibold mb-4">✏️ Editace asistenta</h3>
                <form onSubmit={updateAssistant} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Název asistenta *
                      </label>
                      <input
                        type="text"
                        value={editingAssistant.name}
                        onChange={(e) => setEditingAssistant({ ...editingAssistant, name: e.target.value })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Funkce *
                      </label>
                      <select
                        value={editingAssistant.functionKey}
                        onChange={(e) => setEditingAssistant({ ...editingAssistant, functionKey: e.target.value })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        {Object.entries(availableFunctions).map(([key, func]) => (
                          <option key={key} value={key}>
                            {func.name} ({func.inputType} → {func.outputType})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Pořadí *
                      </label>
                      <input
                        type="number"
                        value={editingAssistant.order}
                        onChange={(e) => setEditingAssistant({ ...editingAssistant, order: parseInt(e.target.value) || 1 })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        min="1"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Timeout (s)
                      </label>
                      <input
                        type="number"
                        value={editingAssistant.timeout}
                        onChange={(e) => setEditingAssistant({ ...editingAssistant, timeout: parseInt(e.target.value) || 60 })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        min="1"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Heartbeat (s)
                      </label>
                      <input
                        type="number"
                        value={editingAssistant.heartbeat}
                        onChange={(e) => setEditingAssistant({ ...editingAssistant, heartbeat: parseInt(e.target.value) || 15 })}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        min="1"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Popis
                    </label>
                    <textarea
                      value={editingAssistant.description}
                      onChange={(e) => setEditingAssistant({ ...editingAssistant, description: e.target.value })}
                      className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={2}
                    />
                  </div>

                  {/* OpenAI parametry sekce */}
                  <div className="border-t pt-4 mt-4">
                    <h4 className="text-md font-semibold text-gray-700 mb-2 flex items-center gap-2">
                      🤖 OpenAI parametry
                      <span className="text-sm font-normal text-gray-500">(pouze pro AI funkce)</span>
                    </h4>
                    <p className="text-sm text-gray-600 mb-4 bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
                      💡 <strong>Tyto hodnoty určují chování asistenta při práci s GPT modelem.</strong> 
                      Můžete je přizpůsobit pro kreativní, informativní nebo technické výstupy.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Model *
                        </label>
                        <select
                          value={editingAssistant.model}
                          onChange={(e) => setEditingAssistant({ ...editingAssistant, model: e.target.value })}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          title="Výběr OpenAI modelu - GPT-4o je nejnovější a nejschopnější"
                        >
                          <option value="gpt-4o">GPT-4o (nejnovější)</option>
                          <option value="gpt-4">GPT-4 (robustní)</option>
                          <option value="gpt-3.5-turbo">GPT-3.5 Turbo (rychlý)</option>
                        </select>
                        <p className="text-xs text-gray-500 mt-1">Nejnovější model pro nejlepší výsledky</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Temperature (0.1-2.0) *
                        </label>
                        <input
                          type="number"
                          value={editingAssistant.temperature}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value);
                            if (val >= 0.1 && val <= 2.0) {
                              setEditingAssistant({ ...editingAssistant, temperature: val });
                            }
                          }}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          min="0.1"
                          max="2.0"
                          step="0.1"
                          placeholder="0.7"
                          title="Nižší = přesnější, Vyšší = kreativnější (0.1 až 2.0)"
                        />
                        <p className="text-xs text-gray-500 mt-1">Nižší = přesnější, Vyšší = kreativnější</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Top P (0-1) *
                        </label>
                        <input
                          type="number"
                          value={editingAssistant.top_p}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value);
                            if (val >= 0 && val <= 1) {
                              setEditingAssistant({ ...editingAssistant, top_p: val });
                            }
                          }}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          min="0"
                          max="1"
                          step="0.1"
                          placeholder="0.9"
                          title="Rozsah 0 až 1 – výběr ze širšího spektra odpovědí"
                        />
                        <p className="text-xs text-gray-500 mt-1">Rozsah 0 až 1 – výběr ze širšího spektra odpovědí</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Max tokens (100-4000) *
                        </label>
                        <input
                          type="number"
                          value={editingAssistant.max_tokens}
                          onChange={(e) => {
                            const val = parseInt(e.target.value);
                            if (val >= 100 && val <= 4000) {
                              setEditingAssistant({ ...editingAssistant, max_tokens: val });
                            }
                          }}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          min="100"
                          max="4000"
                          step="100"
                          placeholder="800"
                          title="Maximální délka odpovědi (100 až 4000)"
                        />
                        <p className="text-xs text-gray-500 mt-1">Maximální délka odpovědi</p>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        System prompt (volitelný)
                      </label>
                      <textarea
                        value={editingAssistant.system_prompt}
                        onChange={(e) => {
                          if (e.target.value.length <= 10000) {
                            setEditingAssistant({ ...editingAssistant, system_prompt: e.target.value });
                          }
                        }}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                        placeholder="Např. 'Jsi kreativní SEO expert, který tvoří briefy pro viral obsah...'"
                        maxLength={10000}
                        title="Např. 'Jsi kreativní SEO expert, který tvoří briefy…' (max. 10000 znaků)"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {editingAssistant.system_prompt.length}/10000 znaků - Definuje roli a styl asistenta
                      </p>
                    </div>
                  </div>

                  {/* UX metadata sekce */}
                  <div className="border-t pt-4 mt-4">
                    <h4 className="text-md font-semibold text-gray-700 mb-2 flex items-center gap-2">
                      👤 Admin metadata
                      <span className="text-sm font-normal text-gray-500">(popis a kontext)</span>
                    </h4>
                    <p className="text-sm text-gray-600 mb-4 bg-green-50 p-3 rounded-lg border-l-4 border-green-400">
                      📋 <strong>Tyto hodnoty pomáhají adminovi pochopit účel a chování asistenta.</strong> 
                      Zlepšují orientaci při správě orchestrátoru.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Popis asistenta (use case)
                        </label>
                        <input
                          type="text"
                          value={editingAssistant.use_case}
                          onChange={(e) => setEditingAssistant({ ...editingAssistant, use_case: e.target.value })}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="Např. 'Generuje SEO brief pro LLM optimalizaci'"
                          title="Krátké shrnutí, co asistent dělá"
                        />
                        <p className="text-xs text-gray-500 mt-1">Krátké shrnutí, co asistent dělá</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Fáze pipeline *
                        </label>
                        <select
                          value={editingAssistant.pipeline_stage}
                          onChange={(e) => setEditingAssistant({ ...editingAssistant, pipeline_stage: e.target.value })}
                          className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          title="Fáze v procesu zpracování"
                        >
                          <option value="">Vyberte fázi...</option>
                          <option value="brief">Brief</option>
                          <option value="research">Research</option>
                          <option value="factvalidation">FactValidation</option>
                          <option value="draft">Draft</option>
                          <option value="humanizer">Humanizer</option>
                          <option value="seo">SEO</option>
                          <option value="multimedia">Multimedia</option>
                          <option value="qa">QA</option>
                          <option value="publish">Publish</option>
                        </select>
                        <p className="text-xs text-gray-500 mt-1">Fáze v workflow pipeline</p>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Styl odpovědi (volitelný)
                      </label>
                      <textarea
                        value={editingAssistant.style_description}
                        onChange={(e) => {
                          if (e.target.value.length <= 1000) {
                            setEditingAssistant({ ...editingAssistant, style_description: e.target.value });
                          }
                        }}
                        className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                        placeholder="Např. 'Stručný, přímý styl s důrazem na jednoduchost a čitelnost'"
                        maxLength={1000}
                        title="Popis stylu odpovědí asistenta (max 1000 znaků)"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {editingAssistant.style_description.length}/1000 znaků - Jak má asistent odpovídat
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={editingAssistant.active}
                        onChange={(e) => setEditingAssistant({ ...editingAssistant, active: e.target.checked })}
                        className="mr-2"
                      />
                      <span className="text-sm text-gray-700">Aktivní</span>
                    </label>
                  </div>

                  <div className="flex gap-3">
                    <button
                      type="submit"
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
                    >
                      ✅ Uložit změny
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingAssistant(null)}
                      className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-lg"
                    >
                      ❌ Zrušit
                    </button>
                  </div>
                </form>
              </div>
            )}

            {project.assistants.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <div className="text-6xl mb-4">🤖</div>
                <h3 className="text-xl font-medium text-gray-600 mb-2">Žádní asistenti</h3>
                <p className="text-gray-500 mb-6">Přidejte asistenty pro vytvoření workflow</p>
                <button
                  onClick={() => setShowAddAssistant(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg"
                >
                  ➕ Přidat prvního asistenta
                </button>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
                <table className="min-w-[1200px] w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Pořadí
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Asistent
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Funkce
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Timeout
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Akce
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {project.assistants
                      .sort((a, b) => a.order - b.order)
                      .map((assistant) => {
                        const status = getAssistantStatus(assistant.functionKey);
                        return (
                          <tr key={assistant.id} className={!assistant.active ? 'opacity-60' : ''}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-medium">
                                {assistant.order}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div>
                                <div className="text-sm font-medium text-gray-900">
                                  {assistant.name}
                                  {!assistant.active && <span className="ml-2 text-xs text-gray-400">(neaktivní)</span>}
                                </div>
                                {assistant.description && (
                                  <div className="text-sm text-gray-500">{assistant.description}</div>
                                )}
                                
                                {/* UX metadata */}
                                <div className="mt-2 space-y-1">
                                  {assistant.use_case && (
                                    <div className="text-xs text-blue-600 flex items-center gap-1" title="Use case">
                                      <span>📝</span>
                                      <span>{assistant.use_case}</span>
                                    </div>
                                  )}
                                  
                                  {assistant.pipeline_stage && (
                                    <div className="text-xs text-purple-600 flex items-center gap-1" title="Pipeline stage">
                                      <span>🔄</span>
                                      <span className="font-mono bg-purple-50 px-1 rounded">{assistant.pipeline_stage}</span>
                                    </div>
                                  )}
                                  
                                  {assistant.style_description && (
                                    <div className="text-xs text-green-600 flex items-center gap-1" title="Style description">
                                      <span>🎨</span>
                                      <span className="italic">
                                        {assistant.style_description.length > 50 
                                          ? `${assistant.style_description.substring(0, 50)}...` 
                                          : assistant.style_description}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <code className="text-xs bg-gray-100 px-2 py-1 rounded font-mono">
                                {assistant.functionKey}
                              </code>
                              <div className="text-xs text-gray-500 mt-1">
                                {assistant.inputType} → {assistant.outputType}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getAssistantStatusColor(status)}`}>
                                {status === 'EXISTING' ? '✅ Existuje' : '❌ Chybí'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <div>Timeout: {assistant.timeout}s</div>
                              <div>Heartbeat: {assistant.heartbeat}s</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <div className="flex gap-2">
                                <button 
                                  onClick={() => startEditAssistant(assistant)}
                                  className="text-blue-600 hover:text-blue-800 p-1 rounded transition-colors"
                                  title="Upravit asistenta"
                                >
                                  ✏️
                                </button>
                                <button 
                                  onClick={() => deleteAssistant(assistant.id, assistant.name)}
                                  className="text-red-600 hover:text-red-800 p-1 rounded transition-colors"
                                  title="Smazat asistenta"
                                >
                                  🗑️
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Workflow Runs Tab */}
        {activeTab === 'runs' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold">🏃‍♂️ Workflow běhy</h2>
              <button
                onClick={() => {
                  const topic = prompt('Zadejte téma pro nový workflow:');
                  if (topic?.trim()) {
                    runWorkflow(topic.trim());
                  }
                }}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg"
              >
                ▶️ Spustit nový běh
              </button>
            </div>

            {workflowRuns.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <div className="text-6xl mb-4">🏃‍♂️</div>
                <h3 className="text-xl font-medium text-gray-600 mb-2">Žádné běhy</h3>
                <p className="text-gray-500 mb-6">Spusťte první workflow pro tento projekt</p>
                <button
                  onClick={() => {
                    const topic = prompt('Zadejte téma pro první workflow:');
                    if (topic?.trim()) {
                      runWorkflow(topic.trim());
                    }
                  }}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg"
                >
                  ▶️ Spustit první workflow
                </button>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Téma
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Doba běhu
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Fáze
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Spuštěno
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Akce
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {workflowRuns.map((run) => (
                      <tr key={run.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-lg">{getStatusEmoji(run.status)}</span>
                          <span className="ml-2 text-sm font-medium">{run.status}</span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900 max-w-xs truncate">
                            {run.topic}
                          </div>
                          <div className="text-xs text-gray-500 font-mono">
                            {run.runId.substring(0, 8)}...
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDuration(run.elapsedSeconds)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {run.stageCount || 0} / {run.totalStages || '?'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(run.startedAt)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <Link 
                            href={`/projects/${projectId}/${run.id}`}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            🔍 Detail
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal pro editaci projektu */}
      {showEditProject && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Upravit projekt</h2>
              <button
                onClick={() => setShowEditProject(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            <form onSubmit={updateProject} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Název projektu *
                </label>
                <input
                  type="text"
                  value={editProjectData.name}
                  onChange={(e) => setEditProjectData({ ...editProjectData, name: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="např. SEO Blog Automator"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Jazyk
                </label>
                <select
                  value={editProjectData.language}
                  onChange={(e) => setEditProjectData({ ...editProjectData, language: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="cs">Čeština (cs)</option>
                  <option value="en">English (en)</option>
                  <option value="sk">Slovenčina (sk)</option>
                  <option value="de">Deutsch (de)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Popis (volitelný)
                </label>
                <textarea
                  value={editProjectData.description}
                  onChange={(e) => setEditProjectData({ ...editProjectData, description: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Stručný popis účelu projektu..."
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg"
                >
                  💾 Uložit změny
                </button>
                <button
                  type="button"
                  onClick={() => setShowEditProject(false)}
                  className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 font-medium py-2 px-4 rounded-lg"
                >
                  Zrušit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
} 