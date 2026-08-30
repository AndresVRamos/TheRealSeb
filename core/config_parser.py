"""
Parser para config.py - Lee y escribe configuraciones preservando formato

Este modulo permite:
- Parsear config.py y extraer variables organizadas por secciones
- Guardar cambios preservando comentarios y formato original
- Validar valores segun su tipo esperado
"""
import re
import ast
import shutil
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Ruta al archivo config.py
CONFIG_PATH = Path(__file__).parent / "config.py"

# Longitud maxima permitida para strings
MAX_STRING_LENGTH = 1000


def infer_type(value: Any) -> str:
    """
    Infiere el tipo de dato para mostrar el control apropiado en UI.

    Args:
        value: Valor a analizar

    Returns:
        Tipo como string: 'bool', 'int', 'float', 'tuple', 'str', 'none'
    """
    if value is None:
        return "none"
    elif isinstance(value, bool):  # bool antes de int (bool es subclase de int)
        return "bool"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, tuple):
        return "tuple"
    else:
        return "str"


def parse_value(value_str: str) -> Tuple[Any, str]:
    """
    Parsea un string de valor y retorna (valor, tipo).
    Usa ast.literal_eval para seguridad.

    Args:
        value_str: String con el valor (ej: '60', 'True', '(30, 215, 96)')

    Returns:
        Tupla (valor_parseado, tipo_inferido)
    """
    try:
        value = ast.literal_eval(value_str.strip())
        return value, infer_type(value)
    except (ValueError, SyntaxError):
        # Si no se puede parsear, tratarlo como string
        return value_str.strip().strip('"\''), "str"


def parse_config() -> Dict[str, Dict[str, Any]]:
    """
    Parsea config.py y retorna un diccionario estructurado por secciones.

    Returns:
        Diccionario con estructura:
        {
            "NOMBRE_SECCION": {
                "variables": [
                    {
                        "name": "VARIABLE_NAME",
                        "value": valor_actual,
                        "type": "int" | "float" | "bool" | "str" | "tuple" | "none",
                        "comment": "comentario opcional",
                        "line_number": 42
                    },
                    ...
                ]
            },
            ...
        }
    """
    config_data = {}
    current_section = "GENERAL"  # Seccion por defecto

    # Regex para detectar secciones: # === NOMBRE ===
    section_pattern = re.compile(r'^#\s*===\s*(.+?)\s*===$')

    # Regex para detectar asignaciones: NOMBRE = valor  # comentario opcional
    # Soporta valores multilinea con parentesis
    assignment_pattern = re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*(.+?)(?:\s*#\s*(.*))?$')

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, start=1):
        line_stripped = line.strip()

        # Detectar seccion
        section_match = section_pattern.match(line_stripped)
        if section_match:
            current_section = section_match.group(1).strip()
            if current_section not in config_data:
                config_data[current_section] = {"variables": []}
            continue

        # Detectar asignacion
        assignment_match = assignment_pattern.match(line_stripped)
        if assignment_match:
            var_name = assignment_match.group(1)
            value_str = assignment_match.group(2)
            comment = assignment_match.group(3) or ""

            # Parsear el valor
            value, var_type = parse_value(value_str)

            # Asegurar que la seccion existe
            if current_section not in config_data:
                config_data[current_section] = {"variables": []}

            config_data[current_section]["variables"].append({
                "name": var_name,
                "value": value,
                "type": var_type,
                "comment": comment.strip(),
                "line_number": line_num
            })

    return config_data


def validate_value(name: str, value: Any, expected_type: str) -> Tuple[bool, str]:
    """
    Valida que un valor sea correcto para el tipo esperado.

    Args:
        name: Nombre de la variable
        value: Valor a validar
        expected_type: Tipo esperado ('int', 'float', 'bool', 'str', 'tuple', 'none')

    Returns:
        Tupla (es_valido, mensaje_error)
    """
    # Permitir None para tipos que lo soportan
    if value is None:
        if expected_type in ("none", "str"):
            return True, ""
        # Verificar si el nombre sugiere que acepta None
        if "BROWSER" in name or "GUILD_ID" in name:
            return True, ""
        return False, "Este campo no acepta valores nulos"

    if expected_type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            return False, "Debe ser un numero entero"

        # Validaciones especificas por nombre
        if "TIMEOUT" in name and value < 0:
            return False, "El timeout no puede ser negativo"
        if "LIMIT" in name and value < 1:
            return False, "El limite debe ser al menos 1"
        if "SIZE" in name and value < 1:
            return False, "El tamano debe ser al menos 1"

    elif expected_type == "float":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False, "Debe ser un numero"

        if "VOLUME" in name and (value < 0 or value > 1):
            return False, "El volumen debe estar entre 0.0 y 1.0"
        if "THRESHOLD" in name and (value < 0 or value > 1):
            return False, "El umbral debe estar entre 0.0 y 1.0"
        if "PERCENTAGE" in name and (value < 0 or value > 1):
            return False, "El porcentaje debe estar entre 0.0 y 1.0"

    elif expected_type == "bool":
        if not isinstance(value, bool):
            return False, "Debe ser True o False"

    elif expected_type == "tuple":
        if not isinstance(value, (tuple, list)):
            return False, "Debe ser una tupla"

        if "RGB" in name:
            if len(value) != 3:
                return False, "Debe tener 3 componentes (R, G, B)"
            for i, v in enumerate(value):
                if not isinstance(v, int) or v < 0 or v > 255:
                    return False, f"Componente {i+1} debe ser un entero entre 0 y 255"

    elif expected_type == "str":
        if value is not None and not isinstance(value, str):
            return False, "Debe ser una cadena de texto"

        if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
            return False, f"El texto no puede exceder {MAX_STRING_LENGTH} caracteres"

        if name == "BOT_PREFIX" and (not value or len(value) == 0):
            return False, "El prefijo no puede estar vacio"

    return True, ""


def format_value_for_write(value: Any, var_type: str) -> str:
    """
    Formatea un valor para escribirlo en config.py.

    Args:
        value: Valor a formatear
        var_type: Tipo del valor

    Returns:
        String formateado para escribir en el archivo
    """
    if value is None:
        return "None"
    elif var_type == "bool":
        return "True" if value else "False"
    elif var_type == "str":
        # Escapar comillas y usar comillas dobles
        escaped = str(value).replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    elif var_type == "tuple":
        # Convertir lista a tupla si es necesario
        if isinstance(value, list):
            value = tuple(value)
        return repr(value)
    else:
        return repr(value)


def save_config(changes: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Guarda cambios en config.py preservando formato y comentarios.

    Args:
        changes: Diccionario {"VARIABLE_NAME": nuevo_valor, ...}

    Returns:
        Tupla (exito, mensaje)
    """
    if not changes:
        return True, "No hay cambios que guardar"

    # Obtener configuracion actual para conocer tipos
    current_config = parse_config()
    var_types = {}
    for section_data in current_config.values():
        for var in section_data["variables"]:
            var_types[var["name"]] = var["type"]

    # Validar cambios antes de guardar
    for name, value in changes.items():
        expected_type = var_types.get(name, "str")
        valid, error_msg = validate_value(name, value, expected_type)
        if not valid:
            return False, f"Error en {name}: {error_msg}"

    # Verificar patrones peligrosos en strings
    dangerous_patterns = ['import ', '__', 'exec(', 'eval(', 'os.', 'sys.', 'subprocess']
    for name, value in changes.items():
        if isinstance(value, str):
            for pattern in dangerous_patterns:
                if pattern in value:
                    return False, f"Valor no permitido en {name}: contiene patron peligroso"

    # Crear backup
    backup_path = CONFIG_PATH.with_suffix('.py.bak')
    try:
        shutil.copy(CONFIG_PATH, backup_path)
    except Exception as e:
        return False, f"Error creando backup: {e}"

    try:
        # Leer archivo original
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Regex para detectar asignaciones
        assignment_pattern = re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*(.+?)(\s*#\s*.*)?$')

        # Procesar lineas
        new_lines = []
        for line in lines:
            line_stripped = line.rstrip('\n\r')
            match = assignment_pattern.match(line_stripped)

            if match:
                var_name = match.group(1)
                if var_name in changes:
                    # Obtener el comentario existente (si hay)
                    comment = match.group(3) or ""

                    # Formatear nuevo valor
                    var_type = var_types.get(var_name, "str")
                    new_value = format_value_for_write(changes[var_name], var_type)

                    # Reconstruir linea preservando formato
                    new_line = f"{var_name} = {new_value}{comment}\n"
                    new_lines.append(new_line)
                    continue

            new_lines.append(line)

        # Escribir archivo modificado
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        # Validar que el archivo resultante sea importable
        spec = importlib.util.spec_from_file_location("config_test", CONFIG_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return True, "Configuracion guardada correctamente"

    except SyntaxError as e:
        # Restaurar backup si hay error de sintaxis
        shutil.copy(backup_path, CONFIG_PATH)
        return False, f"Error de sintaxis en el archivo: {e}"
    except Exception as e:
        # Restaurar backup en caso de cualquier error
        shutil.copy(backup_path, CONFIG_PATH)
        return False, f"Error guardando configuracion: {e}"


def get_config_for_api() -> Dict[str, Any]:
    """
    Obtiene la configuracion formateada para la API.
    Convierte tuplas a listas para serializacion JSON.

    Returns:
        Diccionario listo para jsonify
    """
    config = parse_config()

    # Convertir tuplas a listas para JSON
    for section_data in config.values():
        for var in section_data["variables"]:
            if isinstance(var["value"], tuple):
                var["value"] = list(var["value"])

    return config
