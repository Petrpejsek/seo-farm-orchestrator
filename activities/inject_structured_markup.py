from temporalio import activity

@activity.defn
async def inject_structured_markup(content: str) -> str:
    """
    Přidá JSON-LD schema markup k obsahu, aby byl čitelný pro AI/LLM.
    """
    schema_markup = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": "Co je AI-friendly SEO?",
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "AI-friendly SEO je optimalizace obsahu tak, aby byl snadno čitelný pro LLM systémy."
    }
  }]
}
</script>
"""
    return content + "\n\n" + schema_markup 