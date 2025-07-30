'use client'

import { useState, useEffect } from 'react'

interface ApiKeyModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function ApiKeyModal({ isOpen, onClose }: ApiKeyModalProps) {
  const [openaiKey, setOpenaiKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingKeys, setLoadingKeys] = useState(false)
  const [deletingKey, setDeletingKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [currentKeys, setCurrentKeys] = useState<{ [key: string]: string }>({})

  // Načíst současné API klíče když se modal otevře
  const fetchCurrentKeys = async () => {
    if (!isOpen) return
    
    setLoadingKeys(true)
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${apiBaseUrl}/api-keys`)
      
      if (response.ok) {
        const data = await response.json()
        setCurrentKeys(data.api_keys || {})
      }
    } catch (err) {
      console.error('Chyba při načítání API klíčů:', err)
    } finally {
      setLoadingKeys(false)
    }
  }

  useEffect(() => {
    fetchCurrentKeys()
    // Reset formulář při otevření
    if (isOpen) {
      setOpenaiKey('')
      setError(null)
      setSuccess(false)
    }
  }, [isOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!openaiKey.trim()) {
      setError('API klíč nemůže být prázdný')
      return
    }

    if (!openaiKey.startsWith('sk-')) {
      setError('OpenAI API klíč musí začínat "sk-"')
      return
    }

    if (openaiKey.length > 200) {
      setError('API klíč je příliš dlouhý (maximum 200 znaků)')
      return
    }

    if (openaiKey.length < 20) {
      setError('API klíč je příliš krátký (minimum 20 znaků)')
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${apiBaseUrl}/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          service: 'openai',
          api_key: openaiKey
        })
      })

      if (response.ok) {
        setSuccess(true)
        setOpenaiKey('')
        // Refresh API keys list
        fetchCurrentKeys()
        
        // Auto-close modal po úspěšném uložení
        setTimeout(() => {
          onClose()
        }, 2000)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Chyba při ukládání API klíče')
      }
    } catch (err) {
      setError('Chyba při komunikaci se serverem')
      console.error('Error saving API key:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteKey = async (service: string) => {
    if (!window.confirm(`Opravdu chcete smazat API klíč pro službu "${service}"? Tato akce je nevratná.`)) {
      return
    }

    setDeletingKey(service)
    setError(null)

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${apiBaseUrl}/api-keys/${service}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Refresh API keys list
        fetchCurrentKeys()
        setSuccess(true)
        setTimeout(() => setSuccess(false), 3000)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Chyba při mazání API klíče')
      }
    } catch (err) {
      setError('Chyba při komunikaci se serverem')
      console.error('Error deleting API key:', err)
    } finally {
      setDeletingKey(null)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">🔑 Správa API klíčů</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-xl font-bold"
            >
              ×
            </button>
          </div>

          {/* Současný stav API klíčů */}
          <div className="mb-6 p-3 bg-gray-50 rounded-lg">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Současné API klíče:</h3>
            {loadingKeys ? (
              <div className="text-sm text-gray-500">Načítám...</div>
            ) : Object.keys(currentKeys).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(currentKeys).map(([service, maskedKey]) => (
                  <div key={service} className="flex items-center justify-between p-2 bg-white rounded border">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="capitalize font-medium text-sm flex-shrink-0">{service}:</span>
                      <span className="text-green-600 font-mono text-sm truncate max-w-xs" title={maskedKey}>
                        {maskedKey} ✅
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteKey(service)}
                      disabled={deletingKey === service}
                      className="text-red-500 hover:text-red-700 disabled:text-gray-400 text-sm font-medium px-2 py-1 hover:bg-red-50 rounded transition-colors flex-shrink-0"
                      title={`Smazat ${service} API klíč`}
                    >
                      {deletingKey === service ? '⏳' : '🗑️ Smazat'}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">Žádné API klíče nejsou uloženy</div>
            )}
          </div>

          {/* Formulář pro nový/aktualizaci klíče */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="openai-key" className="block text-sm font-medium text-gray-700 mb-2">
                OpenAI API Key
              </label>
              <input
                id="openai-key"
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
            </div>

            {/* Error message */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="text-sm text-red-600">❌ {error}</div>
              </div>
            )}

            {/* Success message */}
            {success && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="text-sm text-green-600">✅ Operace byla úspěšně dokončena!</div>
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                disabled={loading}
              >
                Zrušit
              </button>
              <button
                type="submit"
                disabled={loading || !openaiKey.trim()}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {loading ? '⏳ Ukládám...' : '💾 Uložit'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
} 