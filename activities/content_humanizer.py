from temporalio import activity

@activity.defn
async def humanize_content(raw_text: str) -> str:
    """Simuluje zlidštění AI textu – přidá přirozené výrazy"""
    phrases = [
        "Let's be honest,",
        "Here's the deal,",
        "What nobody tells you is that",
        "So, in plain English,",
        "Think of it this way:"
    ]
    return f"{phrases[0]} {raw_text.capitalize()} – and trust me, it actually works!" 