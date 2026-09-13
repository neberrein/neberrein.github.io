# Render a code-native social card with the original profile photograph.
# The photograph is never regenerated or retouched; only scaled to fit in full.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$shareRoot = Split-Path -Parent $PSScriptRoot
$shareSource = Join-Path $shareRoot 'dist/assets/images/profile.jpg'
$shareDirectory = Join-Path $shareRoot 'dist/assets/og'
New-Item -ItemType Directory -Path $shareDirectory -Force | Out-Null
$shareOutput = Join-Path $shareDirectory 'profile-share.jpg'
$sharePhoto = [System.Drawing.Image]::FromFile($shareSource)
$shareCanvas = [System.Drawing.Bitmap]::new(1200, 630)
$shareGraphics = [System.Drawing.Graphics]::FromImage($shareCanvas)
$shareGraphics.Clear([System.Drawing.Color]::White)
$shareGraphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$shareGraphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$shareNavy = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#10283f'))
$shareBlue = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#2f5874'))
$shareNameFont = [System.Drawing.Font]::new('Malgun Gothic', 72, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$shareTitleFont = [System.Drawing.Font]::new('Malgun Gothic', 38, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$shareBodyFont = [System.Drawing.Font]::new('Malgun Gothic', 27, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
try {
    $sharePhotoWidth = [single](630 * $sharePhoto.Width / $sharePhoto.Height)
    $shareGraphics.DrawImage($sharePhoto, [single](1200 - $sharePhotoWidth), [single]0, $sharePhotoWidth, [single]630)
    $shareGraphics.DrawString('곽민재', $shareNameFont, $shareNavy, [single]60, [single]164)
    $shareGraphics.DrawString('연구개발 포트폴리오', $shareTitleFont, $shareNavy, [single]64, [single]270)
    $shareGraphics.DrawString('센서융합 · 상태 추정', $shareBodyFont, $shareBlue, [single]66, [single]348)
    $shareGraphics.DrawString('경로 계획 · 임베디드 SW', $shareBodyFont, $shareBlue, [single]66, [single]394)
    $shareJpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
    $shareOptions = [System.Drawing.Imaging.EncoderParameters]::new(1)
    $shareOptions.Param[0] = [System.Drawing.Imaging.EncoderParameter]::new([System.Drawing.Imaging.Encoder]::Quality, [long]95)
    try { $shareCanvas.Save($shareOutput, $shareJpeg, $shareOptions) }
    finally { $shareOptions.Dispose() }
    Write-Output 'Profile social card: 1200 x 630 JPEG, original photograph preserved.'
}
finally {
    $shareNameFont.Dispose(); $shareTitleFont.Dispose(); $shareBodyFont.Dispose()
    $shareNavy.Dispose(); $shareBlue.Dispose()
    $shareGraphics.Dispose(); $shareCanvas.Dispose(); $sharePhoto.Dispose()
}
