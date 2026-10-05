param(
    [string]$Horario = "06:00",
    [string]$NomeTarefa = "ValidadorOSC-AtualizarBases"
)

$ErrorActionPreference = "Stop"
$projeto = Split-Path -Parent $PSScriptRoot
$uv = (Get-Command uv -ErrorAction Stop).Source
$log = Join-Path $projeto "var\atualizacao.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null

$comando = "Set-Location '$projeto'; & '$uv' run --no-sync validador-osc atualizar-bases *>> '$log'"
$acao = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -NonInteractive -Command `"$comando`""
$gatilho = New-ScheduledTaskTrigger -Daily -At $Horario
$opcoes = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho -Settings $opcoes -Force | Out-Null
Write-Output "Tarefa '$NomeTarefa' agendada para $Horario todos os dias. Log em $log"
