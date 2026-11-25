param(
  [Parameter(Mandatory = $true)][string]$OutputPath,
  [Parameter(Mandatory = $true)][string]$Title,
  [Parameter(Mandatory = $true)][string]$Concept,
  [Parameter(Mandatory = $true)][string]$Prompt
)

Add-Type -AssemblyName System.Drawing

$width = 1280
$height = 720
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

$rect = New-Object System.Drawing.Rectangle 0, 0, $width, $height
$bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
  $rect,
  [System.Drawing.Color]::FromArgb(17, 46, 79),
  [System.Drawing.Color]::FromArgb(201, 170, 101),
  45
)
$graphics.FillRectangle($bg, $rect)

$panelBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(40, 11, 28, 46))
$panelPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(70, 241, 221, 174), 2)
$graphics.FillRectangle($panelBrush, 36, 36, 1208, 648)
$graphics.DrawRectangle($panelPen, 36, 36, 1208, 648)

$titleFont = New-Object System.Drawing.Font("Microsoft JhengHei", 30, [System.Drawing.FontStyle]::Bold)
$conceptFont = New-Object System.Drawing.Font("Microsoft JhengHei", 18, [System.Drawing.FontStyle]::Regular)
$promptFont = New-Object System.Drawing.Font("Microsoft JhengHei", 23, [System.Drawing.FontStyle]::Regular)
$footerFont = New-Object System.Drawing.Font("Microsoft JhengHei", 16, [System.Drawing.FontStyle]::Regular)

$whiteBrush = [System.Drawing.Brushes]::White
$goldBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 245, 216, 137))
$softBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(230, 247, 240, 224))

$graphics.DrawString($Title, $titleFont, $whiteBrush, (New-Object System.Drawing.RectangleF 72, 72, 1080, 72))
$graphics.DrawString($Concept, $conceptFont, $goldBrush, (New-Object System.Drawing.RectangleF 72, 136, 1080, 40))

$displayPrompt = $Prompt
if ($displayPrompt.Length -gt 340) {
  $displayPrompt = $displayPrompt.Substring(0, 337) + "..."
}

$graphics.DrawString($displayPrompt, $promptFont, $whiteBrush, (New-Object System.Drawing.RectangleF 72, 220, 1120, 260))
$graphics.DrawString("Auto visual placeholder from Prompt for NotebookLM", $footerFont, $softBrush, (New-Object System.Drawing.PointF 72, 592))
$graphics.DrawString("This block can be replaced later by Bible maps, NotebookLM outputs, or generated artwork.", $footerFont, $softBrush, (New-Object System.Drawing.PointF 72, 626))

[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($OutputPath)) | Out-Null
$bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)

$bg.Dispose()
$panelBrush.Dispose()
$panelPen.Dispose()
$titleFont.Dispose()
$conceptFont.Dispose()
$promptFont.Dispose()
$footerFont.Dispose()
$goldBrush.Dispose()
$softBrush.Dispose()
$graphics.Dispose()
$bitmap.Dispose()
