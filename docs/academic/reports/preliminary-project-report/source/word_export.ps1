param([string]$InDocx, [string]$OutDocx, [string]$OutPdf)
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($InDocx, $false, $false)
    for ($pass = 0; $pass -lt 2; $pass++) {
        $doc.Fields.Update() | Out-Null
        foreach ($t in $doc.TablesOfContents) { $t.Update() | Out-Null }
        $doc.Repaginate()
    }
    $pages = $doc.ComputeStatistics(2)
    Write-Output "PAGES=$pages TOCS=$($doc.TablesOfContents.Count)"
    $doc.SaveAs2($OutDocx, 16)
    $doc.ExportAsFixedFormat($OutPdf, 17, $false, 0, 0, 0, 0, 0, $true, $true, 1, $true, $true, $false)
    $doc.Close($false)
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
