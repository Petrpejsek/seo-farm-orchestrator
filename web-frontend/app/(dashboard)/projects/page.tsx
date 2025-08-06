'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Project {
  id: string;
  name: string;
  slug: string;
  language: string;
  description?: string;
  createdAt: string;
  assistantCount: number;
  workflowRunCount: number;
}

interface NewProject {
  name: string;
  language: string;
  description: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProject, setNewProject] = useState<NewProject>({
    name: '',
    language: 'cs',
    description: ''
  });
  const [creating, setCreating] = useState(false);
  
  // Stav pro mazání projektů
  const [deleteConfirm, setDeleteConfirm] = useState<{
    project: Project | null;
    step: 'first' | 'second' | null;
  }>({ project: null, step: null });
  const [deleting, setDeleting] = useState(false);

  // Načtení projektů
  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/projects`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setProjects(data);
      setError('');
    } catch (err) {
      console.error('Error fetching projects:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při načítání projektů: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  // Vytvoření nového projektu
  const createProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProject.name.trim()) return;

    try {
      setCreating(true);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/project`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newProject),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const createdProject = await response.json();
      
      // Vytvoření výchozích asistentů
      try {
        await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/assistant/bulk-create/${createdProject.id}`, {
          method: 'POST',
        });
      } catch (assistantError) {
        console.warn('Error creating default assistants:', assistantError);
      }

      // Reset formuláře a refresh seznamu
      setNewProject({ name: '', language: 'cs', description: '' });
      setShowCreateForm(false);
      fetchProjects();
    } catch (err) {
      console.error('Error creating project:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při vytváření projektu: ${errorMessage}`);
    } finally {
      setCreating(false);
    }
  };

  // Smazání projektu
  const deleteProject = async (project: Project) => {
    try {
      setDeleting(true);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/project/${project.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Reset stavu a refresh seznamu
      setDeleteConfirm({ project: null, step: null });
      fetchProjects();
    } catch (err) {
      console.error('Error deleting project:', err);
      const errorMessage = err instanceof Error ? err.message : 'Neznámá chyba';
      setError(`Chyba při mazání projektu: ${errorMessage}`);
    } finally {
      setDeleting(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const getLanguageFlag = (language: string) => {
    return language === 'cs' ? '🇨🇿' : language === 'en' ? '🇺🇸' : '🌐';
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Načítám projekty...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">📁 SEO Projects</h1>
            <p className="text-gray-600 mt-2">Správa projektů a workflow orchestrátorů</p>
          </div>
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            ➕ Nový projekt
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex">
              <div className="text-red-600">❌</div>
              <div className="ml-3">
                <p className="text-red-800 font-medium">Chyba</p>
                <p className="text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Create Project Form */}
        {showCreateForm && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">➕ Nový projekt</h2>
            <form onSubmit={createProject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Název projektu *
                </label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="např. SEO Blog Generator"
                  required
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Jazyk
                  </label>
                  <select
                    value={newProject.language}
                    onChange={(e) => setNewProject({ ...newProject, language: e.target.value })}
                    className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="cs">🇨🇿 Čeština</option>
                    <option value="en">🇺🇸 Angličtina</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Popis
                </label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Stručný popis účelu projektu..."
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={creating}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-lg"
                >
                  {creating ? 'Vytvářím...' : '✅ Vytvořit projekt'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-lg"
                >
                  ❌ Zrušit
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Projects Grid */}
        {projects.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📂</div>
            <h3 className="text-xl font-medium text-gray-600 mb-2">Žádné projekty</h3>
            <p className="text-gray-500 mb-6">Začněte vytvořením svého prvního SEO projektu</p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg"
            >
              ➕ Vytvořit první projekt
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <div key={project.id} className="bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all p-6">
                <div className="flex items-start justify-between mb-3">
                  <Link href={`/projects/${project.id}`} className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 truncate hover:text-blue-600 cursor-pointer">
                      {project.name}
                    </h3>
                  </Link>
                  <div className="flex items-center gap-2 ml-2">
                    <span className="text-lg">{getLanguageFlag(project.language)}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteConfirm({ project, step: 'first' });
                      }}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50 p-1 rounded transition-colors"
                      title="Smazat projekt"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
                
                <Link href={`/projects/${project.id}`} className="block">
                  {project.description && (
                    <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                      {project.description}
                    </p>
                  )}

                  <div className="space-y-2 mb-4">
                    <div className="flex items-center text-sm text-gray-500">
                      <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                      <span className="font-medium">Slug:</span>
                      <span className="ml-1 font-mono text-xs">{project.slug}</span>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center text-gray-600">
                        <span>🤖</span>
                        <span className="ml-1">{project.assistantCount} asistentů</span>
                      </div>
                      <div className="flex items-center text-gray-600">
                        <span>🏃‍♂️</span>
                        <span className="ml-1">{project.workflowRunCount} běhů</span>
                      </div>
                    </div>
                  </div>

                  <div className="border-t pt-3">
                    <p className="text-xs text-gray-400">
                      Vytvořeno: {formatDate(project.createdAt)}
                    </p>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        )}

        {/* Stats Footer */}
        {projects.length > 0 && (
          <div className="mt-8 bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span>📊 Celkem projektů: <strong>{projects.length}</strong></span>
              <span>🤖 Celkem asistentů: <strong>{projects.reduce((sum, p) => sum + p.assistantCount, 0)}</strong></span>
              <span>🏃‍♂️ Celkem běhů: <strong>{projects.reduce((sum, p) => sum + p.workflowRunCount, 0)}</strong></span>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirm.project && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              {deleteConfirm.step === 'first' && (
                <>
                  <div className="text-center mb-6">
                    <div className="text-4xl mb-3">⚠️</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Smazat projekt "{deleteConfirm.project.name}"?
                    </h3>
                    <p className="text-gray-600 text-sm">
                      Tato akce smaže projekt včetně <strong>{deleteConfirm.project.assistantCount} asistentů</strong> a <strong>{deleteConfirm.project.workflowRunCount} workflow běhů</strong>.
                    </p>
                    <p className="text-red-600 text-sm font-medium mt-2">
                      Tato akce je nevratná!
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => setDeleteConfirm({ project: deleteConfirm.project, step: 'second' })}
                      className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg"
                    >
                      🗑️ Pokračovat ve smazání
                    </button>
                    <button
                      onClick={() => setDeleteConfirm({ project: null, step: null })}
                      className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-lg"
                    >
                      ❌ Zrušit
                    </button>
                  </div>
                </>
              )}

              {deleteConfirm.step === 'second' && (
                <>
                  <div className="text-center mb-6">
                    <div className="text-4xl mb-3">🚨</div>
                    <h3 className="text-lg font-semibold text-red-900 mb-2">
                      FINÁLNÍ POTVRZENÍ
                    </h3>
                    <p className="text-gray-700 text-sm mb-3">
                      Opravdu chcete natrvalo smazat projekt:
                    </p>
                    <div className="bg-red-50 border border-red-200 rounded p-3 mb-3">
                      <p className="font-semibold text-red-900">"{deleteConfirm.project.name}"</p>
                      <p className="text-red-700 text-xs">
                        {deleteConfirm.project.assistantCount} asistentů • {deleteConfirm.project.workflowRunCount} běhů
                      </p>
                    </div>
                    <p className="text-red-600 font-bold text-sm">
                      TATO AKCE JE NEVRATNÁ!
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => deleteProject(deleteConfirm.project!)}
                      disabled={deleting}
                      className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white px-4 py-2 rounded-lg font-semibold"
                    >
                      {deleting ? '⏳ Mazání...' : '💀 ANO, SMAZAT NAVŽDY'}
                    </button>
                    <button
                      onClick={() => setDeleteConfirm({ project: deleteConfirm.project, step: 'first' })}
                      disabled={deleting}
                      className="flex-1 bg-gray-300 hover:bg-gray-400 disabled:bg-gray-300 text-gray-700 px-4 py-2 rounded-lg"
                    >
                      ↩️ Zpět
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 