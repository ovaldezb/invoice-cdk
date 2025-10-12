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
echo ""

# Ejecutar el comando CDK pasado como parámetro
if [ $# -eq 0 ]; then
    echo "🔧 Uso: ./run_cdk.sh [comando_cdk]"
    echo "📝 Ejemplos:"
    echo "   ./run_cdk.sh synth"
    echo "   ./run_cdk.sh deploy"
    echo "   ./run_cdk.sh diff"
    echo "   ./run_cdk.sh destroy"
else
    echo "copying env file"
    cp .env_dev .env
    echo "🚀 Ejecutando: cdk $@"
    echo "----------------------------------------"
    cdk "$@" --profile pagos
    echo "Termino de ejecutar cdk DEV $@"
fi
