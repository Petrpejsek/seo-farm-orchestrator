import random
from temporalio import activity

@activity.defn
async def generate_keywords(topic: str) -> list:
    """Simuluje generování clusteru klíčových slov k tématu"""
    base_keywords = [f"{topic} guide", f"{topic} tips", f"best {topic}", f"{topic} tutorial", f"{topic} strategy"]
    extra = [f"{topic} {x}" for x in ["for beginners", "2025", "step by step", "case study", "examples"]]
    all_keywords = base_keywords + extra
    random.shuffle(all_keywords)
    return all_keywords[:5] 