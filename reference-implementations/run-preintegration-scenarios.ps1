param(
	[string]$BaseUrl = "http://127.0.0.1:8000",
	[string]$PythonExe = ".\\.venv\\Scripts\\python.exe"
)

$ErrorActionPreference = "Stop"

function Write-Section {
	param([string]$Title)
	Write-Host ""
	Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Invoke-ChatScenario {
	param(
		[string]$SessionId,
		[string]$Message,
		[hashtable]$EvidenceOverride
	)

	$payload = @{
		session_id = $SessionId
		message = $Message
		deterministic_response = $true
		evidence_override = $EvidenceOverride
	} | ConvertTo-Json -Depth 6

	return Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/chat" -ContentType "application/json" -Body $payload
}

function Assert-Condition {
	param(
		[bool]$Condition,
		[string]$FailureMessage
	)

	if (-not $Condition) {
		throw $FailureMessage
	}
}

Write-Section "Health Check"
$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/health"
Write-Host "API status: $($health.status) provider=$($health.provider)"
Assert-Condition ($health.status -eq "ok") "API health check failed"

$tempDir = [System.IO.Path]::GetTempPath()
$ctlDir = Join-Path $tempDir "lumina-ctl"
New-Item -ItemType Directory -Path $ctlDir -Force | Out-Null

$noEscSession = "preint-noesc-" + ([guid]::NewGuid().ToString("N").Substring(0, 8))
$escSession = "preint-esc-" + ([guid]::NewGuid().ToString("N").Substring(0, 8))
$exhaustSession = "preint-exhaust-" + ([guid]::NewGuid().ToString("N").Substring(0, 8))

$noEscLedger = Join-Path $ctlDir "session-$noEscSession.jsonl"
$escLedger = Join-Path $ctlDir "session-$escSession.jsonl"
$exhaustLedger = Join-Path $ctlDir "session-$exhaustSession.jsonl"

if (Test-Path $noEscLedger) { Remove-Item $noEscLedger -Force }
if (Test-Path $escLedger) { Remove-Item $escLedger -Force }
if (Test-Path $exhaustLedger) { Remove-Item $exhaustLedger -Force }

Write-Section "Scenario A: Stable Turn (No Escalation)"
$stableEvidence = @{
	correctness = "correct"
	hint_used = $false
	response_latency_sec = 6.0
	frustration_marker_count = 0
	repeated_error = $false
	off_task_ratio = 0.0
	equivalence_preserved = $true
	illegal_operations = @()
	substitution_check = $true
	method_recognized = $true
	step_count = 4
}

$stable = Invoke-ChatScenario -SessionId $noEscSession -Message "I solved it and checked by substitution." -EvidenceOverride $stableEvidence
Write-Host "action=$($stable.action) prompt_type=$($stable.prompt_type) escalated=$($stable.escalated)"
Assert-Condition (-not $stable.escalated) "Expected no escalation in stable scenario"

Write-Section "Scenario B: Major Drift / Escalation"
$escalationEvidence = @{
	correctness = "incorrect"
	hint_used = $true
	response_latency_sec = 18.0
	frustration_marker_count = 3
	repeated_error = $true
	off_task_ratio = 0.2
	equivalence_preserved = $true
	illegal_operations = @()
	substitution_check = $true
	method_recognized = $true
	step_count = 4
}

$escalated = Invoke-ChatScenario -SessionId $escSession -Message "I keep messing this up and I am frustrated." -EvidenceOverride $escalationEvidence
Write-Host "action=$($escalated.action) prompt_type=$($escalated.prompt_type) escalated=$($escalated.escalated)"
Assert-Condition ($escalated.escalated) "Expected escalation in major drift scenario"

Write-Section "Scenario C: Standing Order Exhaustion Escalation"
$loopEvidence = @{
	correctness = "incorrect"
	hint_used = $false
	response_latency_sec = 6.0
	frustration_marker_count = 0
	repeated_error = $true
	off_task_ratio = 0.0
	equivalence_preserved = $false
	illegal_operations = @()
	substitution_check = $true
	method_recognized = $true
	step_count = 2
}

$lastLoopResponse = $null
for ($turn = 1; $turn -le 4; $turn++) {
	$lastLoopResponse = Invoke-ChatScenario -SessionId $exhaustSession -Message "loop turn $turn" -EvidenceOverride $loopEvidence
	Write-Host "turn=$turn action=$($lastLoopResponse.action) escalated=$($lastLoopResponse.escalated)"
}
Assert-Condition ($lastLoopResponse.escalated) "Expected escalation after standing-order max attempts are exhausted"

Write-Section "CTL Ledger Presence"
Assert-Condition (Test-Path $noEscLedger) "No-esc ledger file missing: $noEscLedger"
Assert-Condition (Test-Path $escLedger) "Esc ledger file missing: $escLedger"
Assert-Condition (Test-Path $exhaustLedger) "Exhaust ledger file missing: $exhaustLedger"
Write-Host "No-escalation ledger: $noEscLedger"
Write-Host "Escalation ledger:   $escLedger"
Write-Host "Exhaustion ledger:   $exhaustLedger"

Write-Section "Validate CTL Hash Chain"
& $PythonExe "reference-implementations/ctl-commitment-validator.py" --verify-chain $noEscLedger
Assert-Condition ($LASTEXITCODE -eq 0) "CTL chain validation failed for non-escalation ledger"

& $PythonExe "reference-implementations/ctl-commitment-validator.py" --verify-chain $escLedger
Assert-Condition ($LASTEXITCODE -eq 0) "CTL chain validation failed for escalation ledger"

& $PythonExe "reference-implementations/ctl-commitment-validator.py" --verify-chain $exhaustLedger
Assert-Condition ($LASTEXITCODE -eq 0) "CTL chain validation failed for standing-order exhaustion ledger"

Write-Section "Validate EscalationRecord Exists"
$escRecords = Get-Content $escLedger | ForEach-Object { $_ | ConvertFrom-Json }
$escCount = @($escRecords | Where-Object { $_.record_type -eq "EscalationRecord" }).Count
Assert-Condition ($escCount -ge 1) "Expected EscalationRecord in escalation ledger"
Write-Host "EscalationRecord count: $escCount"

$exhaustRecords = Get-Content $exhaustLedger | ForEach-Object { $_ | ConvertFrom-Json }
$exhaustEscCount = @($exhaustRecords | Where-Object { $_.record_type -eq "EscalationRecord" }).Count
Assert-Condition ($exhaustEscCount -ge 1) "Expected EscalationRecord in standing-order exhaustion ledger"
Write-Host "Exhaustion EscalationRecord count: $exhaustEscCount"

Write-Section "Result"
Write-Host "Pre-integration scenarios passed."
Write-Host "Session IDs: $noEscSession, $escSession, $exhaustSession"
