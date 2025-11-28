{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Animation Plan Schema",
  "type": "object",
  "required": ["title", "core_concept", "educational_domain", "visual_elements", "animation_sequence"],
  "additionalProperties": false,
  "properties": {
    "title": { "type": "string" },
    "core_concept": { "type": "string" },
    "educational_domain": { "type": "string" },
    "visual_elements": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "description"],
        "additionalProperties": false,
        "properties": {
          "id": { "type": "string" },
          "type": {
            "type": "string",
            "enum": ["circle", "rectangle", "triangle", "text", "equation", "image", "arrow", "wave", "parabola", "line"]
          },
          "description": { "type": "string" }
        }
      },
      "minItems": 1
    },
    "animation_sequence": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["step", "title", "action", "elements", "duration", "educational_explanation"],
        "additionalProperties": false,
        "properties": {
          "step": { "type": "integer", "minimum": 1 },
          "title": { "type": "string" },
          "action": { "type": "string" },
          "elements": {
            "type": "array",
            "items": { "type": "string" },
            "minItems": 0
          },
          "duration": { "type": "number", "minimum": 0.1 },
          "educational_explanation": { "type": "string" }
        }
      },
      "minItems": 1
    }
  }
}