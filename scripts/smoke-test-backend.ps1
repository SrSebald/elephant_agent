$ErrorActionPreference = "Stop"

$BaseUrl = if ($env:BACKEND_API_URL) { $env:BACKEND_API_URL.TrimEnd("/") } else { "http://127.0.0.1:8000" }
$SampleFile = Join-Path $PSScriptRoot "sample-ticket.log"

Set-Content -LiteralPath $SampleFile -Value "checkout api returned 500 on promo order in prod"

function Invoke-ApiJson {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Uri,

    [Parameter(Mandatory = $true)]
    [string]$Method
  )

  try {
    return Invoke-RestMethod -Uri $Uri -Method $Method
  } catch {
    $response = $_.Exception.Response
    if ($response -ne $null) {
      $stream = $response.GetResponseStream()
      $reader = New-Object System.IO.StreamReader($stream)
      $body = $reader.ReadToEnd()
      $reader.Close()
      throw "Request to $Uri failed with status $($response.StatusCode): $body"
    }
    throw
  }
}

Write-Host "Checking backend health at $BaseUrl/health"
$health = Invoke-ApiJson -Uri "$BaseUrl/health" -Method Get
$health | ConvertTo-Json -Depth 5

Write-Host ""
Write-Host "Listing tickets"
$ticketsBefore = Invoke-ApiJson -Uri "$BaseUrl/api/v1/tickets" -Method Get
$ticketsBefore | ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "Creating a sample ticket"
$createResponse = curl.exe -s -X POST "$BaseUrl/api/v1/tickets" `
  -F "title=Checkout fails in prod" `
  -F "description=Users cannot finish checkout when a promo code is applied. We need to route this and inspect it." `
  -F "files=@$SampleFile;type=text/plain"

$createResponse

Write-Host ""
Write-Host "Waiting for background processing"
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Listing tickets after processing"
$ticketsAfter = Invoke-ApiJson -Uri "$BaseUrl/api/v1/tickets" -Method Get
$ticketsAfter | ConvertTo-Json -Depth 8

if (Test-Path -LiteralPath $SampleFile) {
  Remove-Item -LiteralPath $SampleFile -Force
}
