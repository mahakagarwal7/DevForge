# Optional modular helper to convert plan JSON -> example (same logic is embedded in pipeline)
import json
from typing import Dict

def plan_to_example(plan: Dict) -> Dict:
    title = plan.get("title") or plan.get("core_concept") or "Explain concept"
    core = plan.get("core_concept", "")
    domain = plan.get("educational_domain", "")
    elems = plan.get("visual_elements", []) or []
    seq = plan.get("animation_sequence", []) or []

    elems_desc = []
    for e in elems:
        elems_desc.append(f"{e.get('id')}({e.get('type')}): {e.get('description','')}")
    seq_desc = []
    for s in seq:
        seq_desc.append(f"{s.get('title','Step')}: {s.get('action','')} on {s.get('elements',[])} - {s.get('educational_explanation','')}")

    output = f"Title: {title}\nCore: {core}\nDomain: {domain}\nElements:\n" + "\n".join(elems_desc) + "\n\nSequence:\n" + "\n".join(seq_desc)
    return {"instruction": f"Create an educational animation plan for: {title}", "input": core, "output": output}