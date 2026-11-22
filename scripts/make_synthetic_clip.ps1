# Generates a SYNTHETIC development clip with Windows' built-in text-to-speech.
# The voice is a stock computer voice: NOT a real person and NOT an imitation of one.
# Never use this clip as the demo recording or present it as a storyteller.
# Each blank-line-separated paragraph in the text file is followed by a 2-second pause.
#
# Run from the repo root:  powershell -File scripts\make_synthetic_clip.ps1
param(
    [string]$TextPath = (Join-Path $PSScriptRoot "..\fixtures\synthetic_story.txt"),
    [string]$OutPath  = (Join-Path $PSScriptRoot "..\data\dev\SYNTHETIC_story.wav"),
    [string]$Voice    = "Microsoft Zira Desktop"
)

Add-Type -AssemblyName System.Speech

$TextPath = [System.IO.Path]::GetFullPath($TextPath)
$OutPath  = [System.IO.Path]::GetFullPath($OutPath)
New-Item -ItemType Directory -Force -Path (Split-Path $OutPath) | Out-Null

$paragraphs = (Get-Content -Raw -Encoding UTF8 $TextPath) -split '(?:\r?\n){2,}' |
    Where-Object { $_.Trim() }

$builder = New-Object System.Speech.Synthesis.PromptBuilder
foreach ($p in $paragraphs) {
    $builder.AppendText($p.Trim())
    $builder.AppendBreak([TimeSpan]::FromSeconds(2))
}

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($Voice)
$synth.Rate = -1
$synth.SetOutputToWaveFile($OutPath)
$synth.Speak($builder)
$synth.Dispose()

Write-Output "Wrote $OutPath ($($paragraphs.Count) paragraphs)"
