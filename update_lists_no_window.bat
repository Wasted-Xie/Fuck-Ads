@echo off
:: 检查是否已经以隐藏后台模式运行，如果不是则重新启动自己
if "%1"=="" (
    powershell -Command "Start-Process -FilePath '%~f0' -ArgumentList 'hide' -WindowStyle Hidden"
    exit /b
)

@echo off
setlocal EnableExtensions
title Update DNS merged lists

rem ============================================================
rem  CONFIG - edit as needed, then save and run this file
rem ============================================================
rem  Target GitHub repository URL (HTTPS or SSH).
rem  Leave empty: push is skipped with a hint unless an origin
rem  remote is already configured in this directory.
set "REMOTE_URL=https://github.com/Wasted-Xie/Fuck-Ads.git"

rem  Branch to create/push (used on first init as the default branch)
set "BRANCH=main"

rem  Python launcher / merge script / output file
set "PY=py"
set "MERGE_SCRIPT=merge_dedup.py"
set "OUT_DIR=out"
set "OUT_NAME=merged_dns_rules.txt"
rem ============================================================

rem  Upstream sources. Each source has a chain of mirror URLs
rem  (space-separated, URLs contain no spaces); mirrors are tried in
rem  order until one succeeds. gh-proxy.com is a general fallback for
rem  raw.githubusercontent.com when direct access or ghfast.top fails.
set "F1=filter_11.txt"
set "F2=goodbyeads_dns.txt"
set "F3=adblockdns.txt"
set "URL1=https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt"
set "URL2=https://ghfast.top/raw.githubusercontent.com/8680/GOODBYEADS/master/data/rules/dns.txt https://raw.githubusercontent.com/8680/GOODBYEADS/master/data/rules/dns.txt https://gh-proxy.com/https://raw.githubusercontent.com/8680/GOODBYEADS/master/data/rules/dns.txt"
set "URL3=https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblockdns.txt https://ghfast.top/raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblockdns.txt https://gh-proxy.com/https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblockdns.txt"

rem ---- Step 1: cd to the directory this script lives in ----
cd /d "%~dp0" || ( echo [ERROR] cannot enter script directory & exit /b 1 )
echo.
echo [1/4] Working dir: %CD%
if not exist raw mkdir raw

rem ---- Step 2: fetch the three upstream rule sources ----
where curl >nul 2>nul
if errorlevel 1 ( echo [ERROR] curl.exe not found ^(Windows 10 1803+ ships it^) & exit /b 1 )

call :fetch "%F1%" "%URL1%"
if errorlevel 1 exit /b 1
call :fetch "%F2%" "%URL2%"
if errorlevel 1 exit /b 1
call :fetch "%F3%" "%URL3%"
if errorlevel 1 exit /b 1

rem ---- Step 3: run the merge/dedup script ----
where py >nul 2>nul
if errorlevel 1 ( echo [ERROR] Python launcher "py" not found. Install Python 3 ^(check "py launcher"^). & exit /b 1 )
echo.
echo [3/4] Running %MERGE_SCRIPT% ...
%PY% "%MERGE_SCRIPT%"
if errorlevel 1 ( echo [ERROR] merge script failed & exit /b 1 )

rem ---- Step 4: commit and push to GitHub ----
echo.
echo [4/4] Pushing to GitHub ...
if "%REMOTE_URL%"=="" (
    git remote get-url origin >nul 2>nul
    if errorlevel 1 (
        echo [SKIP] REMOTE_URL is empty and no origin remote is configured.
        echo        Fill in REMOTE_URL at the top of this file and rerun.
        exit /b 0
    )
)

rem  -- initialize a local git repo if absent --
if not exist ".git" (
    echo Initializing local git repository ...
    git init >nul || ( echo [ERROR] git init failed & exit /b 1 )
    git branch -M "%BRANCH%" || ( echo [ERROR] cannot create branch %BRANCH% & exit /b 1 )
)
git remote get-url origin >nul 2>nul
if errorlevel 1 (
    git remote add origin "%REMOTE_URL%" || ( echo [ERROR] cannot add origin. Check REMOTE_URL. & exit /b 1 )
)

rem  -- bootstrap: fresh local repo (no commits yet) with a remote that
rem     already has history: align HEAD with the remote first --
git rev-parse -q --verify HEAD >nul 2>nul
if errorlevel 1 (
    git ls-remote --exit-code --heads origin "%BRANCH%" >nul 2>nul
    if not errorlevel 1 (
        echo Fresh local repo detected - aligning with remote origin/%BRANCH% ...
        git fetch origin "%BRANCH%" >nul || ( echo [ERROR] git fetch failed & exit /b 1 )
        git reset --hard "origin/%BRANCH%" >nul || ( echo [ERROR] cannot align with remote & exit /b 1 )
    )
)

rem  -- stage the merged file and the scripts (raw/ stays untracked) --
git add "%OUT_DIR%\%OUT_NAME%" "%MERGE_SCRIPT%" .gitignore README.md "%~nx0" || ( echo [ERROR] git add failed & exit /b 1 )
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Update merged DNS rules" || ( echo [ERROR] commit failed. Configure git user first: git config --global user.name/user.email & exit /b 1 )
    rem  -- sync with remote, but only after committing so the tree is clean --
    git ls-remote --exit-code --heads origin "%BRANCH%" >nul 2>nul
    if not errorlevel 1 (
        echo Syncing with remote origin/%BRANCH% ...
        git fetch origin "%BRANCH%" >nul || ( echo [ERROR] git fetch failed & exit /b 1 )
        git rebase "origin/%BRANCH%" || ( echo [ERROR] rebase failed. Resolve conflicts, then rerun. & exit /b 1 )
    )
    git push -u origin "%BRANCH%" || ( echo [ERROR] push failed. Check the repo URL and GitHub credentials ^(HTTPS token or SSH key^). & exit /b 1 )
    echo [DONE] Pushed to origin/%BRANCH%
) else (
    rem  -- nothing to commit: fast-forward local to remote if it moved --
    git ls-remote --exit-code --heads origin "%BRANCH%" >nul 2>nul
    if not errorlevel 1 (
        git fetch origin "%BRANCH%" >nul 2>nul
        git pull --ff-only origin "%BRANCH%" >nul 2>nul
    )
    echo No rule changes - commit and push skipped
)
exit /b 0

rem ============================================================
rem  Helper: download one source file by trying a chain of mirror
rem  URLs until one succeeds. Also rejects empty downloads.
rem  Usage: call :fetch "target-name" "url1 url2 url3 ..."
rem ============================================================
:fetch
set "NAME=%~1"
set "URLS=%~2"
set "TMPF=raw\%NAME%.tmp"
echo.
echo [2/4] Downloading %NAME% ...
for %%u in (%URLS%) do (
    curl -sSL --fail --ssl-no-revoke --retry 1 --connect-timeout 15 --max-time 90 -o "%TMPF%" "%%u" 2>nul
    if not errorlevel 1 goto fetch_ok
    del "%TMPF%" >nul 2>nul
)
echo       [ERROR] download failed: %NAME% ^(all mirrors unreachable^)
del "%TMPF%" >nul 2>nul
exit /b 1

:fetch_ok
for %%A in ("%TMPF%") do if %%~zA EQU 0 (
    echo       [ERROR] download failed: %NAME% ^(empty response^)
    del "%TMPF%" >nul 2>nul
    exit /b 1
)
move /y "%TMPF%" "raw\%NAME%" >nul || ( echo [ERROR] cannot write raw\%NAME% & exit /b 1 )
echo       OK: raw\%NAME%
exit /b 0
