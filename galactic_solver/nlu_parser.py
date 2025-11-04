from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from .challenge_client import ChallengeClient

# Expected deterministic schema from the LLM:
# {
#   "entities": [ {"type": "sw_character"|"sw_planet"|"pokemon", "name": string}, ... ],
#   "vars": { "x1": {"entity": 0, "attribute": string }, ... },
#   "expression": "x1 * x2 + (x3 / 2)",
#   "notes": string
# }

SYSTEM_DEV_MSG = (
    "Eres un parser que convierte un enunciado en español a una expresión matemática basada en atributos de entidades. "
    "Responde SOLO con JSON válido y exactamente con este esquema: {\n"
    "  'entities': [ { 'type': 'sw_character'|'sw_planet'|'pokemon', 'name': string } ],\n"
    "  'vars': { var: { 'entity': number, 'attribute': string } },\n"
    "  'expression': string,\n"
    "  'notes': string\n"
    "}.\n"
    "Atributos válidos: sw_planet -> rotation_period, orbital_period, diameter, surface_water, population, name; "
    "sw_character -> height, mass, homeworld, name; pokemon -> base_experience, height, weight, name.\n"
    "Reglas de mapeo por tipo (MUY IMPORTANTE):\n"
    "- Para pokemon: 'altura' -> height, 'peso' -> weight, 'experiencia base' -> base_experience.\n"
    "- Para sw_character: 'masa' -> mass, 'peso' -> mass, 'altura' -> height, 'planeta natal' -> homeworld.\n"
    "- Para sw_planet: 'diámetro' -> diameter, 'período orbital' -> orbital_period, 'período de rotación' -> rotation_period, 'agua superficial' -> surface_water, 'población' -> population.\n"
    "Si se necesita longitud de un string, utiliza len(name) o len(homeworld) expresándolo con una variable que tome ese string y luego usando len(variable) en la expresión.\n"
    "No incluyas texto adicional, solo JSON."
)


def parse_statement(statement: str, client: ChallengeClient) -> Optional[Dict[str, Any]]:
    messages = [
        {"role": "developer", "content": SYSTEM_DEV_MSG},
        {"role": "user", "content": statement},
    ]
    try:
        resp = client.chat_completion(messages)
        content = resp.get("choices", [{}])[0].get("message", {}).get("content") if isinstance(resp, dict) else None
        if not content:
            return None
        # Ensure pure JSON (strip code fences if any)
        content_str = str(content).strip()
        if content_str.startswith("```"):
            content_str = content_str.strip("` ")
            if content_str.lower().startswith("json"):
                content_str = content_str[4:].strip()
        data = json.loads(content_str)
        # Basic validation
        if not isinstance(data, dict):
            return None
        if "entities" not in data or "vars" not in data or "expression" not in data:
            return None
        return data
    except Exception:
        # One simple retry with stricter reminder
        try:
            messages[0]["content"] += "\nSOLO JSON. NO texto adicional."
            resp = client.chat_completion(messages)
            content = resp.get("choices", [{}])[0].get("message", {}).get("content") if isinstance(resp, dict) else None
            if not content:
                return None
            content_str = str(content).strip()
            if content_str.startswith("```"):
                content_str = content_str.strip("` ")
                if content_str.lower().startswith("json"):
                    content_str = content_str[4:].strip()
            data = json.loads(content_str)
            if not isinstance(data, dict):
                return None
            if "entities" not in data or "vars" not in data or "expression" not in data:
                return None
            return data
        except Exception:
            return None
