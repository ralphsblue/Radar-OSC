# retentar_pendentes.sh - refaz periodicamente (5 min) os casos sem resposta definitiva.
# Uso: RODADAS=8 bash retentar_pendentes.sh >> respostas/_log_roteiro.txt
cd "$(dirname "$0")"
for i in $(seq 1 ${RODADAS:-8}); do
  echo "### rodada $i $(date -u +%FT%TZ)"
  PYTHONIOENCODING=utf-8 ../../.venv/Scripts/python roteiro.py --so-pendentes 2>&1 | grep -v '^$' | grep -v '^== ' 
  n=$(PYTHONIOENCODING=utf-8 ../../.venv/Scripts/python -c "
import json,glob
print(sum(1 for f in glob.glob('respostas/*_*.json') if 'T6' not in f and 'descartado' not in f and json.load(open(f,encoding='utf-8')).get('http') not in (200,400,404)))")
  echo "pendentes: $n"
  [ "$n" = "0" ] && break
  sleep 300
done
