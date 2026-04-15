# V0.3-013 Windows No-Install EXE Build Kit

Šis paketas paruošia **build-ready** Windows `.exe` generavimą iš jau užrakinto v0.3.009 demo bundle.

## Kas sukurta
- `demo_smoke_launcher.py` — launcheris su `pass` ir `error` režimais
- `AI_Workflow_Demo.spec` — PyInstaller spec failas
- `requirements_exe.txt` — priklausomybės EXE buildui
- `build_windows_exe.bat` — vieno veiksmo build skriptas Windows aplinkai
- `.github/workflows/build_windows_exe.yml` — GitHub Actions workflow
- įtraukti visi reikalingi LOCKED failai:
  - `reference_pre_run_validator.py`
  - `reference_pre_run_validator_cli.py`
  - `example_runtime_context.json`
  - `example_ruleset.json`
  - `schemas/*`

## Ką galima paleisti po build
- `AI_Workflow_Demo.exe pass`
- `AI_Workflow_Demo.exe error`

## Ribojimas
Šioje Linux aplinkoje tikras Windows `.exe` nebuvo sugeneruotas, nes nėra Windows build toolchain.
Šis paketas yra skirtas:
- buildinti Windows mašinoje
- arba buildinti per GitHub Actions Windows runner

## Build Windows mašinoje
1. Atidarykite paketą
2. Paleiskite `build_windows_exe.bat`
3. Rezultatas: `dist\AI_Workflow_Demo.exe`

## GitHub Actions
Workflow failas sugeneruos Windows `.exe` artefaktą automatiškai.
