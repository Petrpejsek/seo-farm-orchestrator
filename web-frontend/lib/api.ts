// 🔧 Centrální API konfigurace pro SEO Farm Orchestrator

/**
 * Základní API URL pro backend spojení
 * Fallback na localhost:8000 pro dev prostředí
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * Pomocná funkce pro API volání s automatickým prefixem
 */
export const apiUrl = (endpoint: string): string => {
  // Pokud endpoint už začíná http, vrať ho beze změny
  if (endpoint.startsWith('http')) {
    return endpoint;
  }
  
  // Jinak přidej base URL
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

/**
 * Typované API response pro error handling
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

/**
 * Centralizované fetch s error handlingem
 */
export const apiCall = async <T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> => {
  try {
    const url = apiUrl(endpoint);
    console.log(`🔗 API Call: ${options.method || 'GET'} ${url}`);
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.message || data.detail || `HTTP ${response.status}`,
        data: null,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (error) {
    console.error('🚨 API Call Error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      data: null,
    };
  }
};