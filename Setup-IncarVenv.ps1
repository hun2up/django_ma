Setup-IncarVenv.ps1

<#
    ============================================
      INCA Financial Service - venv Setup Script
      파일명 : Setup-IncarVenv.ps1
      기능   : venv 생성 → 활성화 → 패키지 설치 → requirements.txt 기록
    ============================================
#>

# 1️⃣ 현재 작업 폴더 확인
Write-Host "🔍 현재 경로: $PWD" -ForegroundColor Cyan

# 2️⃣ Python 설치 여부 확인
Write-Host "🐍 Python 버전 확인 중..."
$pythonVersion = & py --version 2>$null
if (-not $pythonVersion) {
    Write-Host "❌ Python이 설치되어 있지 않습니다. PATH에 추가되어 있는지 확인하세요." -ForegroundColor Red
    exit
}
Write-Host "✅ Python 버전: $pythonVersion" -ForegroundColor Green

# 3️⃣ 가상환경 폴더 이름
$venvName = "venv"

# 4️⃣ 기존 venv 폴더가 있으면 삭제 여부 확인
if (Test-Path $venvName) {
    $confirm = Read-Host "⚠️ 기존 '$venvName' 폴더가 존재합니다. 새로 만들까요? (y/n)"
    if ($confirm -eq "y") {
        Remove-Item -Recurse -Force $venvName
        Write-Host "🧹 기존 venv 폴더 삭제 완료." -ForegroundColor Yellow
    } else {
        Write-Host "❌ 스크립트를 종료합니다." -ForegroundColor Red
        exit
    }
}

# 5️⃣ venv 생성
Write-Host "🪄 가상환경 '$venvName' 생성 중..."
py -m venv $venvName
Write-Host "✅ 가상환경 생성 완료." -ForegroundColor Green

# 6️⃣ PowerShell 정책 완화 (현재 세션 한정)
Write-Host "🔐 스크립트 실행 정책 설정 중 (현재 세션 한정)..."
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force

# 7️⃣ 가상환경 활성화
Write-Host "🚀 가상환경 활성화 중..."
. ".\$venvName\Scripts\Activate.ps1"

# 8️⃣ pip 최신화
Write-Host "⬆️ pip 업그레이드 중..."
python -m pip install --upgrade pip

# 9️⃣ 기본 패키지 설치 (필요에 따라 수정 가능)
Write-Host "📦 Django 및 필수 패키지 설치 중..."
pip install django requests pillow openpyxl

# 10️⃣ requirements.txt 생성
Write-Host "📝 requirements.txt 생성 중..."
pip freeze > requirements.txt

# 11️⃣ 결과 요약 출력
Write-Host "n✅ 모든 설정 완료!" -ForegroundColor Green
Write-Host "-------------------------------------------"
Write-Host "📂 가상환경 경로 : $(Get-Item .\$venvName).FullName"
Write-Host "📄 설치된 패키지 : requirements.txt"
Write-Host "💡 다음부터 사용할 때:"
Write-Host "    venv\Scripts\Activate.ps1"
Write-Host "-------------------------------------------"