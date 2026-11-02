@echo off
setlocal
chcp 65001 > nul
title LALGONDAR(8-1)converter

call "%~dp0LALGONDAR_CONVERTER.bat" %*
