from datetime import datetime
from typing import List, Dict, Any
from pymongo.collection import Collection

def buscar_bitacora_por_fechas(fecha_inicio: str, fecha_fin: str, bitacora_collection: Collection) -> List[Dict[str, Any]]:
    """
    Busca registros en la bitácora dentro del rango de fechas especificado.
    
    Args:
        fecha_inicio: Fecha de inicio en formato ISO (YYYY-MM-DDTHH:MM:SS)
        fecha_fin: Fecha de fin en formato ISO (YYYY-MM-DDTHH:MM:SS)
        bitacora_collection: Colección de MongoDB para bitácora
    
    Returns:
        Lista de registros de bitácora que caen dentro del rango de fechas
    """
    try:
        # Convertir strings a objetos datetime si es necesario
        if isinstance(fecha_inicio, str):
            fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
        else:
            fecha_inicio_dt = fecha_inicio
            
        if isinstance(fecha_fin, str):
            fecha_fin_dt = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))
        else:
            fecha_fin_dt = fecha_fin
        
        # Crear el filtro de búsqueda
        filtro = {
            "timestamp": {
                "$gte": fecha_inicio_dt.isoformat(),
                "$lte": fecha_fin_dt.isoformat()
            }
        }
        
        # Ejecutar la búsqueda y ordenar por timestamp descendente
        registros = list(bitacora_collection.find(filtro).sort("timestamp", -1))
        #obten los registros
        no_registros = len(registros)
        # Convertir ObjectId a string para serialización JSON
        for registro in registros:
            if '_id' in registro:
                registro['_id'] = str(registro['_id'])
        #regresa los registros y el numero de registros
        return registros, no_registros
        
    except Exception as e:
        print(f"Error al buscar en bitácora: {str(e)}")
        return [], 0
