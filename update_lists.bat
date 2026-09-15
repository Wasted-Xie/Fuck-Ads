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

rem  Python launcher / scripts / output file
set "PY=py"
set "MERGE_SCRIPT=merge_dedup.py"
set "INTEGRATE_SCRIPT=integrate_sources.py"
set "OUT_DIR=out"
set "OUT_NAME=merged_dns_rules.txt"

rem  Source directories (both stay untracked)
set "RAW_DIR=raw"
set "EXTRA_DIR=sources"
rem ============================================================

rem  Primary sources (3). Each has a chain of mirror URLs
rem  (space-separated, URLs contain no spaces); mirrors are tried in
rem  order until one succeeds.
set "F1=filter_11.txt"
set "F2=goodbyeads_dns.txt"
set "F3=adblockdns.txt"
set "URL1=https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt"
set "URL2=https://ghfast.top/raw.githubusercontent.com/8680/GOODBYEADS/master/data/rules/dns.txt https://raw.githubusercontent.com/8680/GOODBYEADS/master/data/rules/dns.txt https://gh-proxy.com/https://raw.githubusercontent.com/8680/GOODBYEADS/master/data/rules/dns.txt"
set "URL3=https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblockdns.txt https://ghfast.top/raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblockdns.txt https://gh-proxy.com/https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblockdns.txt"

rem ---- Step 1: cd to the directory this script lives in ----
cd /d "%~dp0" || ( echo [ERROR] cannot enter script directory & exit /b 1 )
echo.
echo [1/5] Working dir: %CD%
if not exist "%RAW_DIR%" mkdir "%RAW_DIR%"
if not exist "%EXTRA_DIR%" mkdir "%EXTRA_DIR%"

rem ---- Step 2: fetch the three primary upstream rule sources ----
where curl >nul 2>nul
if errorlevel 1 ( echo [ERROR] curl.exe not found ^(Windows 10 1803+ ships it^) & exit /b 1 )

call :fetch "%F1%" "%URL1%"
if errorlevel 1 exit /b 1
call :fetch "%F2%" "%URL2%"
if errorlevel 1 exit /b 1
call :fetch "%F3%" "%URL3%"
if errorlevel 1 exit /b 1

rem ---- Step 3: fetch additional upstream sources (18 lists) ----
rem  Failures here are non-fatal: only a warning, then continue.
rem  GitHub sources go through a mirror chain (single requests succeed
rem  while rapid bursts get rejected, so mirrors rotate with a delay).
echo.
echo [3/5] Fetching additional sources ...
call :fetch_gh "yhosts.txt"        "https://raw.githubusercontent.com/VeleSila/yhosts/master/hosts"
call :fetch_gh "ad-wars.txt"       "https://raw.githubusercontent.com/jdlingyu/ad-wars/master/hosts"
call :fetch_gh "1024_hosts.txt"    "https://raw.githubusercontent.com/Goooler/1024_hosts/master/hosts"
call :fetch_gh "adaway.txt"        "https://raw.githubusercontent.com/AdAway/adaway.github.io/master/hosts.txt"
call :fetch_gh "youslist.txt"      "https://raw.githubusercontent.com/yous/YousList/master/hosts.txt"
call :fetch_gh "stevenblack.txt"   "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
call :fetch_gh "xinggsf-rule.txt"  "https://raw.githubusercontent.com/xinggsf/Adblock-Plus-Rule/master/rule.txt"
call :fetch_gh "xinggsf-mv.txt"    "https://raw.githubusercontent.com/xinggsf/Adblock-Plus-Rule/master/mv.txt"
call :fetch_gh "adgk.txt"          "https://raw.githubusercontent.com/banbendalao/ADgk/master/ADgk.txt"
call :fetch_gh "cjx-annoyance.txt" "https://raw.githubusercontent.com/cjx82630/cjxlist/master/cjx-annoyance.txt"
call :fetch_gh "anti-ad.txt"       "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-adguard.txt"
call :fetch_direct "mvps.txt"             "https://winhelp2002.mvps.org/hosts.txt"
call :fetch_direct "abp-easyprivacy.txt"  "https://easylist-downloads.adblockplus.org/easyprivacy.txt"
call :fetch_direct "easylist.txt"         "https://easylist.to/easylist/easylist.txt"
call :fetch_direct "easylist-privacy.txt" "https://easylist.to/easylist/easyprivacy.txt"
call :fetch_direct "easylistchina.txt"    "https://easylist-downloads.adblockplus.org/easylistchina.txt"
call :fetch_direct "idontcarecookies.txt" "https://www.i-dont-care-about-cookies.eu/abp/"
call :fetch_direct "antiadblock.txt"      "https://easylist-downloads.adblockplus.org/antiadblockfilters.txt"

rem ---- Step 4: clean the extra sources, then merge everything ----
where py >nul 2>nul
if errorlevel 1 ( echo [ERROR] Python launcher "py" not found. Install Python 3 ^(check "py launcher"^). & exit /b 1 )
echo.
echo [4/5] Running %INTEGRATE_SCRIPT% ...
%PY% "%INTEGRATE_SCRIPT%"
if errorlevel 1 echo [WARN] integrate step failed - extra sources will be skipped
echo.
echo [4/5] Running %MERGE_SCRIPT% ...
%PY% "%MERGE_SCRIPT%"
if errorlevel 1 ( echo [ERROR] merge script failed & exit /b 1 )

rem ---- Step 5: commit and push to GitHub ----
echo.
echo [5/5] Pushing to GitHub ...
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

rem  -- stage the merged file and the scripts (raw/ and sources/ stay untracked) --
git add "%OUT_DIR%\%OUT_NAME%" "%MERGE_SCRIPT%" "%INTEGRATE_SCRIPT%" .gitignore README.md "%~nx0" || ( echo [ERROR] git add failed & exit /b 1 )
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
rem  Helper: download one PRIMARY source by trying a chain of
rem  mirror URLs until one succeeds. Rejects empty downloads.
rem  Usage: call :fetch "target-name" "url1 url2 url3 ..."
rem ============================================================
:fetch
set "NAME=%~1"
set "URLS=%~2"
set "TMPF=%RAW_DIR%\%NAME%.tmp"
echo.
echo [2/5] Downloading %NAME% ...
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
move /y "%TMPF%" "%RAW_DIR%\%NAME%" >nul || ( echo [ERROR] cannot write %RAW_DIR%\%NAME% & exit /b 1 )
echo       OK: %RAW_DIR%\%NAME%
exit /b 0

rem ============================================================
rem  Helper: download an EXTRA source from GitHub through a chain of
rem  mirrors, with a short pause between attempts. Non-fatal on
rem  failure (only a warning). Usage: call :fetch_gh "name" "raw-url"
rem ============================================================
:fetch_gh
set "NAME=%~1"
set "RAW=%~2"
set "TMPF=%EXTRA_DIR%\%NAME%.tmp"
echo       %NAME% ...
for %%P in (https://gh-proxy.com/ https://gh.ddlc.top/ https://gh.con.sh/ https://ghproxy.cn/ https://ghfast.top/) do (
    curl -sSL --fail --ssl-no-revoke --retry 1 --connect-timeout 12 --max-time 150 -o "%TMPF%" "%%P%RAW%" 2>nul
    if not errorlevel 1 goto fetch_gh_ok
    del "%TMPF%" >nul 2>nul
    ping -n 3 127.0.0.1 >nul
)
curl -sSL --fail --ssl-no-revoke --connect-timeout 15 --max-time 150 -o "%TMPF%" "%RAW%" 2>nul
if errorlevel 1 (
    echo       [WARN] %NAME% failed on all mirrors - skipped
    del "%TMPF%" >nul 2>nul
    exit /b 1
)

:fetch_gh_ok
call :check_and_move "%NAME%" || exit /b 1
exit /b 0

rem ============================================================
rem  Helper: download an EXTRA source directly (non-GitHub hosts).
rem  Usage: call :fetch_direct "name" "url"
rem ============================================================
:fetch_direct
set "NAME=%~1"
set "URL=%~2"
set "TMPF=%EXTRA_DIR%\%NAME%.tmp"
echo       %NAME% ...
curl -sSL --fail --ssl-no-revoke --retry 2 --connect-timeout 15 --max-time 150 -o "%TMPF%" "%URL%" 2>nul
if errorlevel 1 (
    echo       [WARN] %NAME% download failed - skipped
    del "%TMPF%" >nul 2>nul
    exit /b 1
)
call :check_and_move "%NAME%" || exit /b 1
exit /b 0

rem ============================================================
rem  Helper: reject empty extra download, otherwise move into place.
rem  Usage: call :check_and_move "name"
rem ============================================================
:check_and_move
set "NAME=%~1"
set "TMPF=%EXTRA_DIR%\%NAME%.tmp"
if not exist "%TMPF%" (
    echo       [WARN] %NAME% missing - skipped
    exit /b 1
)
for %%A in ("%TMPF%") do if %%~zA EQU 0 (
    echo       [WARN] %NAME% empty response - skipped
    del "%TMPF%" >nul 2>nul
    exit /b 1
)
move /y "%TMPF%" "%EXTRA_DIR%\%NAME%" >nul
if errorlevel 1 (
    echo       [WARN] cannot write %EXTRA_DIR%\%NAME%
    exit /b 1
)
echo       OK: %EXTRA_DIR%\%NAME%
exit /b 0
