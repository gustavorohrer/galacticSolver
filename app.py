#!/usr/bin/env python3
from __future__ import annotations
import argparse
import os
import sys
import time
from decimal import Decimal
from typing import Optional

from dotenv import load_dotenv

from galactic_solver.challenge_client import ChallengeClient
from galactic_solver.nlu_parser import parse_statement
from galactic_solver.evaluator import eval_expression
from galactic_solver.data_sources import swapi, pokeapi
from galactic_solver.utils import parse_decimal


def solve_statement(statement: str, client: ChallengeClient) -> Optional[Decimal]:
    parsed = parse_statement(statement, client)
    if not parsed:
        print("[WARN] No se pudo parsear el enunciado (parser/LLM)")
        return None

    entities = parsed.get("entities", [])
    vars_spec = parsed.get("vars", {})
    expression = parsed.get("expression", "")

    # Resolver entidades
    resolved = []
    for e in entities:
        etype = (e.get("type") or "").lower()
        name = e.get("name")
        if not isinstance(name, str):
            print("[WARN] Entidad sin nombre válido")
            return None
        item = None
        if etype == "sw_character":
            item = swapi.get_character(name)
        elif etype == "sw_planet":
            item = swapi.get_planet(name)
        elif etype == "pokemon":
            item = pokeapi.get_pokemon(name)
        else:
            print(f"[WARN] Tipo de entidad no soportado: {etype}")
            return None
        if not item:
            print(f"[WARN] No se encontró entidad: {etype} - {name}")
            return None
        resolved.append(item)

    # Construir variables para el evaluador
    variables: dict[str, object] = {}

    PLANET_ATTRS = {"rotation_period", "orbital_period", "diameter", "surface_water", "population", "name"}
    CHAR_ATTRS = {"height", "mass", "homeworld", "name"}
    POKE_ATTRS = {"base_experience", "height", "weight", "name"}

    def attr_allowed_for(etype: str, attr: str) -> bool:
        if etype == "sw_planet":
            return attr in PLANET_ATTRS
        if etype == "sw_character":
            return attr in CHAR_ATTRS
        if etype == "pokemon":
            return attr in POKE_ATTRS
        return False

    for var, spec in vars_spec.items():
        if not isinstance(spec, dict):
            print(f"[WARN] Especificación de variable inválida: {var}")
            return None
        idx = spec.get("entity")
        attr = spec.get("attribute")
        if not isinstance(idx, int) or not isinstance(attr, str):
            print(f"[WARN] Variable {var} sin 'entity' (int) o 'attribute' (str)")
            return None
        if idx < 0 or idx >= len(resolved):
            print(f"[WARN] Índice de entidad fuera de rango para {var}")
            return None

        # Normalización por tipo para evitar deslices (p.ej., 'mass' vs 'weight')
        etype = (entities[idx].get("type") or "").lower()
        if etype == "pokemon" and attr == "mass":
            attr = "weight"
        if etype == "sw_character" and attr == "weight":
            attr = "mass"

        # Si el atributo no es válido para el tipo actual o falta el valor, intentar una reasignación segura por tipo
        value = resolved[idx].get(attr)
        if (not attr_allowed_for(etype, attr)) or (value is None):
            # Determinar tipos candidatos según el atributo
            if attr in PLANET_ATTRS:
                wanted_type = "sw_planet"
            elif attr in CHAR_ATTRS:
                wanted_type = "sw_character"
            elif attr in POKE_ATTRS:
                wanted_type = "pokemon"
            else:
                wanted_type = etype
            # Buscar candidatos con ese tipo que tengan el atributo disponible
            candidates: list[int] = []
            for j, ent in enumerate(entities):
                if (ent.get("type") or "").lower() == wanted_type:
                    val_j = resolved[j].get(attr)
                    if val_j is not None:
                        candidates.append(j)
            chosen = None
            if len(candidates) == 1:
                chosen = candidates[0]
            elif len(candidates) > 1:
                # Heurística: si el nombre de la entidad aparece en el nombre de la variable, preferir ese
                var_low = var.lower()
                for j in candidates:
                    ent_name = str(entities[j].get("name") or "").lower()
                    if ent_name and ent_name in var_low:
                        chosen = j
                        break
                if chosen is None:
                    chosen = candidates[0]
            if chosen is not None and chosen != idx:
                print(f"[WARN] Reasignando variable {var} del índice {idx} ({etype}) a {chosen} ({(entities[chosen].get('type') or '').lower()}) por atributo '{attr}'.")
                idx = chosen
                etype = (entities[idx].get("type") or "").lower()
                value = resolved[idx].get(attr)

        if value is None:
            print(f"[WARN] Atributo faltante para {var}: {attr} en entidad {idx} ({etype}).")
            return None
        # Normalizar números (si vienen como string) a Decimal/int
        if isinstance(value, str):
            # Mantener strings (para len())
            variables[var] = value
        else:
            d = parse_decimal(value)
            if d is None:
                print(f"[WARN] No se pudo convertir a número: {var}={value}")
                return None
            variables[var] = d

    try:
        result = eval_expression(expression, variables)
        return result
    except ZeroDivisionError:
        print("[WARN] División por cero en la expresión — se salta el problema")
        return None
    except Exception as ex:
        print(f"[WARN] Error evaluando la expresión: {ex}")
        return None


def cmd_practice(args):
    client = ChallengeClient()
    test = client.get_test()
    # Intentar detectar campos comunes
    statement = None
    for k in ("statement", "problem", "enunciado", "text"):
        if k in test and isinstance(test[k], str):
            statement = test[k]
            break
    if not statement:
        print("[INFO] Respuesta /challenge/test:")
        print(test)
        print("[ERROR] No se encontró el campo del enunciado en la respuesta de práctica.")
        return 1

    expected = None
    for k in ("expected", "solution", "answer", "resultado"):
        if k in test:
            expected = test[k]
            break

    print("\n[TEST] Enunciado:")
    print(statement)
    result = solve_statement(statement, client)
    if result is None:
        print("[FAIL] No se pudo resolver el problema de práctica.")
        return 1
    # Imprimir resultado con 10 decimales fijo
    print(f"[OK] Resultado calculado: {result:.10f}")
    if expected is not None:
        print(f"[INFO] Esperado (según API): {expected}")
    return 0


def cmd_official(args):
    client = ChallengeClient()
    start_data = client.start()
    problem_id = start_data.get("problem_id") or start_data.get("id")
    statement = start_data.get("statement") or start_data.get("problem") or start_data.get("text")

    if not problem_id or not isinstance(statement, str):
        print("[ERROR] Respuesta inesperada de /challenge/start:")
        print(start_data)
        return 1

    print("[INFO] Comienza el intento oficial (3 minutos)")
    t0 = time.time()
    LIMIT_SECONDS = 175  # margen de seguridad

    while time.time() - t0 < LIMIT_SECONDS and problem_id and isinstance(statement, str):
        remaining = int(LIMIT_SECONDS - (time.time() - t0))
        print(f"\n[PROBLEMA] ID={problem_id} (tiempo restante ~{remaining}s)")
        ans = solve_statement(statement, client)
        if ans is None:
            # Enviar 0 para pasar al siguiente, estrategia simple
            answer_payload = 0
            print("[INFO] Enviando 0 para continuar al siguiente problema.")
        else:
            answer_payload = float(ans)  # enviar como número
            print(f"[INFO] Enviando respuesta: {ans:.10f}")
        try:
            resp = client.submit_solution(str(problem_id), answer_payload)
        except Exception as ex:
            print(f"[ERROR] Falló el envío de solución: {ex}")
            break
        # Siguiente problema
        problem_id = resp.get("problem_id") or resp.get("id")
        statement = resp.get("statement") or resp.get("problem") or resp.get("text")

    print("\n[INFO] Fin del intento oficial.")
    return 0


def main():
    load_dotenv()  # cargar .env si existe

    parser = argparse.ArgumentParser(description="galacticSolver - Desafío cronometrado")
    sub = parser.add_subparsers(dest="command")

    p1 = sub.add_parser("practice", help="Ejecuta el endpoint de práctica y resuelve el problema retornado")
    p1.set_defaults(func=cmd_practice)

    p2 = sub.add_parser("official", help="Inicia el intento oficial (3 minutos)")
    p2.set_defaults(func=cmd_official)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
