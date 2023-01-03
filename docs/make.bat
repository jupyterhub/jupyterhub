@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=--color -W --keep-going
)
if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=source
set BUILDDIR=_build

if "%1" == "" goto help
if "%1" == "devenv" goto devenv
goto default


:default
%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Open and read README.md!
	exit /b 1
)
%SPHINXBUILD% -M %1 "%SOURCEDIR%" "%BUILDDIR%" %SPHINXOPTS%
goto end


:help
%SPHINXBUILD% -M help "%SOURCEDIR%" "%BUILDDIR%" %SPHINXOPTS%
goto end


:devenv
sphinx-autobuild >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-autobuild' command was not found. Open and read README.md!
	exit /b 1
)
sphinx-autobuild -b html --open-browser "%SOURCEDIR%" "%BUILDDIR%/html"
goto end


:end
popd
