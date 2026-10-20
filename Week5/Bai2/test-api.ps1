param([string]$BaseUrl = 'http://127.0.0.1:5003/api/v1/books')
$ErrorActionPreference = 'Stop'
$offsetRows = @()
$offset = 0
while ($true) {
    $page = Invoke-RestMethod "${BaseUrl}?strategy=offset&genre=tech&sort=-price,title&limit=3&offset=$offset"
    $offsetRows += @($page.data)
    if (-not $page.pagination.has_next) { break }
    $offset += 3
    if ($offset -gt 10000) { throw 'Offset loop did not terminate' }
}
$cursorRows = @()
$cursor = $null
for ($i = 0; $i -lt 1000; $i++) {
    $url = "${BaseUrl}?strategy=cursor&genre=tech&sort=-price,title&limit=3"
    if ($cursor) { $url += '&cursor=' + [uri]::EscapeDataString($cursor) }
    $page = Invoke-RestMethod $url
    $cursorRows += @($page.data)
    if (-not $page.page.more) { break }
    $cursor = $page.page.next
    if (-not $cursor) { throw 'Missing next cursor' }
}
if ($page.page.more) { throw 'Cursor loop did not terminate' }
if ($cursorRows.Count -eq 0) { throw 'Seed the database first' }
if (($offsetRows.id -join ',') -ne ($cursorRows.id -join ',')) { throw 'Order mismatch' }
if (@($cursorRows.id | Select-Object -Unique).Count -ne $cursorRows.Count) { throw 'Duplicate IDs' }
if (@($cursorRows | Where-Object { $_.category.slug -ne 'tech' }).Count -gt 0) { throw 'Genre filter failed' }
Write-Output "PASS: offset and cursor return the same $($cursorRows.Count) tech books in the same order."
Write-Output 'PASS: no duplicate IDs, genre filter is correct.'
$cursorRows | Select-Object id,title,@{Name='price';Expression={$_.price.amount}} | Format-Table
