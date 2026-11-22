!define VOXCRAFT_INSTALLER_HOOK_DIR "${__FILEDIR__}"

!macro NSIS_HOOK_PREINSTALL
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  ClearErrors
  File /oname=install_vbcable.ps1 "${VOXCRAFT_INSTALLER_HOOK_DIR}\install_vbcable.ps1"
  IfErrors vbcable_failed

  ClearErrors
  ExecWait '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\install_vbcable.ps1" -CheckOnly' $0
  IfErrors vbcable_failed
  ${If} $0 == 0
    Goto vbcable_ready
  ${EndIf}
  ${If} $0 != 1
    Goto vbcable_failed
  ${EndIf}

  ; Download automatically in interactive and passive mode. The driver setup
  ; still requests elevation through Windows when needed.
  IfSilent vbcable_no_ui
  DetailPrint "Baixando e instalando o VB-Audio Virtual Cable / Downloading and installing VB-Audio Virtual Cable"
  ClearErrors
  ExecWait '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\install_vbcable.ps1"' $0
  IfErrors vbcable_failed
  ${If} $0 == 0
    Goto vbcable_ready
  ${EndIf}

vbcable_failed:
  IfSilent vbcable_no_ui
  SetDetailsView show
  DetailPrint "Não foi possível confirmar a instalação do VB-Audio Virtual Cable."
  DetailPrint "Could not verify the VB-Audio Virtual Cable installation."
  SetErrorLevel 1
  Abort "VB-Audio Virtual Cable installation failed."

vbcable_no_ui:
  SetErrorLevel 1
  Abort "VB-Audio Virtual Cable is required. Run the installer interactively."

vbcable_ready:
  ; Tauri copies the main executable relative to $OUTDIR after this hook.
  SetOutPath "$INSTDIR"
!macroend
