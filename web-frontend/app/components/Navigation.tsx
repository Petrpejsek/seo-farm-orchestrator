'use client'

import { useState } from 'react'
import Link from 'next/link'
import ApiKeyModal from './ApiKeyModal'

export default function Navigation() {
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false)

  return (
    <>
      <nav className="bg-white shadow-sm border-b border-gray-200 p-4">
        <div className="max-w-6xl mx-auto">
          <div className="flex justify-between items-center">
            <div className="flex gap-6">
              <Link href="/" className="text-blue-600 hover:text-blue-800 font-medium">
                🏠 Dashboard
              </Link>
              <Link href="/projects" className="text-blue-600 hover:text-blue-800 font-medium">
                📁 Projects
              </Link>
              <Link href="/workflows" className="text-blue-600 hover:text-blue-800 font-medium">
                ⚙️ Workflows
              </Link>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsApiKeyModalOpen(true)}
                className="px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2"
                title="Spravovat API klíče"
              >
                🔑 API klíče
              </button>
              <div className="text-sm text-gray-500 font-medium">
                SEO Farm Orchestrator
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* API Key Management Modal */}
      <ApiKeyModal 
        isOpen={isApiKeyModalOpen} 
        onClose={() => setIsApiKeyModalOpen(false)} 
      />
    </>
  )
} 