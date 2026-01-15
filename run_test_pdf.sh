#!/bin/bash

# Script para ejecutar comandos CDK con la configuración personalizada de dependencias
# Configurar PYTHONPATH para incluir la carpeta requirements

export PYTHONPATH="/Users/macbookpro/git/invoice-cdk/requirements:$PYTHONPATH"

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Entorno virtual activado"
fi

echo "✅ PYTHONPATH configurado para usar ./requirements/"
echo "📁 PYTHONPATH actual: $PYTHONPATH"

python main1.py