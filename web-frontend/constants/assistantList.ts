/**
 * Finální specifikace 9 asistentů pro SEO Farm Orchestrator
 * 
 * KRITICKÉ: Toto pořadí MUSÍ odpovídat backend implementaci!
 * Každá změna zde vyžaduje odpovídající změnu v backend/activities/assistant_activities.py
 */

export interface AssistantConfig {
  id: string;
  name: string;
  slug: string;
  order: number;
  icon: string;
  color: string;
  bgColor: string;
  description: string;
  inputType: string;
  outputType: string;
  apiType: 'GPT' | 'DALLE';
  model: string;
  estimatedDuration: number; // v sekundách
}

/**
 * ❌ STATICKÝ SEZNAM ODSTRANĚN - používáme dynamické načítání z databáze
 * Všechny komponenty musí načítat asistenty přes API
 */
/*
// CELÝ STATICKÝ SEZNAM ZAKOMENTOVÁN - používáme dynamické načítání
export const FINAL_ASSISTANTS: AssistantConfig[] = [
  {
    id: "brief_assistant",
    name: "BriefAssistant",
    slug: "brief_assistant",
    order: 1,
    icon: "📝",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    description: "Vytváří strukturovaný brief projektu na základě zadaného tématu",
    inputType: "topic",
    outputType: "brief",
    apiType: "GPT",
    model: "gpt-4o",
    estimatedDuration: 30
  },
  {
    id: "research_assistant",
    name: "ResearchAssistant", 
    slug: "research_assistant",
    order: 2,
    icon: "🔍",
    color: "text-green-600",
    bgColor: "bg-green-50",
    description: "Provádí detailní výzkum tématu, sbírá data a trendy",
    inputType: "brief",
    outputType: "research_data",
    apiType: "GPT",
    model: "gpt-4o",
    estimatedDuration: 60
  },
  {
    id: "fact_validator_assistant",
    name: "FactValidatorAssistant",
    slug: "fact_validator_assistant", 
    order: 3,
    icon: "✅",
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    description: "Ověřuje faktickou správnost a validuje zdrojové informace",
    inputType: "research_data",
    outputType: "validated_facts",
    apiType: "GPT",
    model: "gpt-4o",
    estimatedDuration: 45
  },
  {
    id: "draft_assistant",
    name: "DraftAssistant",
    slug: "draft_assistant",
    order: 4,
    icon: "✍️",
    color: "text-orange-600", 
    bgColor: "bg-orange-50",
    description: "Vytváří první draft článku na základě validovaných dat",
    inputType: "validated_facts",
    outputType: "content_draft",
    apiType: "GPT",
    model: "gpt-4o",
    estimatedDuration: 90
  },
  {
    id: "humanizer_assistant",
    name: "HumanizerAssistant",
    slug: "humanizer_assistant",
    order: 5,
    icon: "👤",
    color: "text-pink-600",
    bgColor: "bg-pink-50", 
    description: "Humanizuje obsah pro lepší čitelnost a engagement",
    inputType: "content_draft",
    outputType: "humanized_content",
    apiType: "GPT",
    model: "gpt-4o",
    estimatedDuration: 60
  },
  {
    id: "seo_assistant",
    name: "SEOAssistant",
    slug: "seo_assistant",
    order: 6,
    icon: "📈",
    color: "text-indigo-600",
    bgColor: "bg-indigo-50",
    description: "Optimalizuje obsah pro vyhledávače a SEO best practices",
    inputType: "humanized_content", 
    outputType: "seo_optimized_content",
    apiType: "GPT",
    model: "gpt-4o",
    estimatedDuration: 45
  },
  {
    id: "multimedia_assistant",
    name: "MultimediaAssistant",
    slug: "multimedia_assistant",
    order: 7,
    icon: "🎬",
    color: "text-yellow-600",
    bgColor: "bg-yellow-50",
    description: "Navrhuje multimedia elementy a vytváří prompty pro obrázky",
    inputType: "seo_optimized_content",
    outputType: "multimedia_suggestions", 
    apiType: "GPT",
    model: "gpt-4o",
    estimatedDuration: 30
  },
  {
    id: "qa_assistant", 
    name: "QAAssistant",
    slug: "qa_assistant",
    order: 8,
    icon: "🔍",
    color: "text-red-600",
    bgColor: "bg-red-50",
    description: "Provádí quality assurance a finální kontrolu kvality",
    inputType: "multimedia_suggestions",
    outputType: "qa_report",
    apiType: "GPT", 
    model: "gpt-4o",
    estimatedDuration: 30
  },
  {
    id: "image_renderer_assistant",
    name: "ImageRendererAssistant",
    slug: "image_renderer_assistant",
    order: 9,
    icon: "🎨", 
    color: "text-violet-600",
    bgColor: "bg-violet-50",
    description: "Generuje obrázky pomocí FAL.AI API na základě multimedia návrhů",
    inputType: "multimedia_suggestions",
    outputType: "generated_images",
    apiType: "IMAGE",
    model: "imagen-4",
    estimatedDuration: 120
  }
];

/**
 * Helper funkce pro práci s asistenty
 */

export const getAssistantBySlug = (slug: string): AssistantConfig | undefined => {
  return FINAL_ASSISTANTS.find(assistant => assistant.slug === slug);
};

export const getAssistantByOrder = (order: number): AssistantConfig | undefined => {
  return FINAL_ASSISTANTS.find(assistant => assistant.order === order);
};

export const getAssistantIcon = (stageName: string): string => {
  const assistant = FINAL_ASSISTANTS.find(
    a => a.name === stageName || a.slug === stageName
  );
  return assistant?.icon || "⚙️";
};

export const getAssistantColor = (stageName: string): string => {
  const assistant = FINAL_ASSISTANTS.find(
    a => a.name === stageName || a.slug === stageName
  );
  return assistant?.color || "text-gray-600";
};

export const getAssistantBgColor = (stageName: string): string => {
  const assistant = FINAL_ASSISTANTS.find(
    a => a.name === stageName || a.slug === stageName
  );
  return assistant?.bgColor || "bg-gray-50";
};

export const getTotalEstimatedDuration = (): number => {
  return FINAL_ASSISTANTS.reduce((total, assistant) => total + assistant.estimatedDuration, 0);
};

export const getAssistantProgress = (completedOrder: number): number => {
  return Math.round((completedOrder / FINAL_ASSISTANTS.length) * 100);
};

/**
 * VALIDAČNÍ KONSTANTY
 */
export const EXPECTED_ASSISTANT_COUNT = 9;
export const EXPECTED_ORDER_SEQUENCE = [1, 2, 3, 4, 5, 6, 7, 8, 9];

/**
 * Validace konfigurace asistentů
 */
export const validateAssistantConfiguration = (): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];
  
  // Kontrola počtu asistentů
  if (FINAL_ASSISTANTS.length !== EXPECTED_ASSISTANT_COUNT) {
    errors.push(`Očekáváno ${EXPECTED_ASSISTANT_COUNT} asistentů, ale máme ${FINAL_ASSISTANTS.length}`);
  }
  
  // Kontrola unikátních order
  const orders = FINAL_ASSISTANTS.map(a => a.order);
  const uniqueOrders = Array.from(new Set(orders));
  if (orders.length !== uniqueOrders.length) {
    errors.push("Duplicitní order hodnoty detekována");
  }
  
  // Kontrola správného pořadí
  const sortedOrders = [...orders].sort((a, b) => a - b);
  if (JSON.stringify(sortedOrders) !== JSON.stringify(EXPECTED_ORDER_SEQUENCE)) {
    errors.push(`Chybné pořadí: očekáváno ${EXPECTED_ORDER_SEQUENCE}, máme ${sortedOrders}`);
  }
  
  // Kontrola unikátních ID a slugů
  const ids = FINAL_ASSISTANTS.map(a => a.id);
  const slugs = FINAL_ASSISTANTS.map(a => a.slug);
  if (ids.length !== new Set(ids).size) {
    errors.push("Duplicitní ID asistentů");
  }
  if (slugs.length !== new Set(slugs).size) {
    errors.push("Duplicitní slugy asistentů");
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// Spustíme validaci při importu
const validation = validateAssistantConfiguration();
if (!validation.isValid) {
  console.error("❌ CHYBA V KONFIGURACI ASISTENTŮ:", validation.errors);
  // V produkci by zde měla být exception
}
*/

// Poznámka: Všechny komponenty používající AssistantConfig musí nyní
// načítat data dynamicky z API místo použití statické konstanty