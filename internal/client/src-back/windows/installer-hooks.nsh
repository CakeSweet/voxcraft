!define VOXCRAFT_INSTALLER_HOOK_DIR "${__FILEDIR__}"

!macro NSIS_HOOK_PREINSTALL
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File /oname=install_vbcable.ps1 "${VOXCRAFT_INSTALLER_HOOK_DIR}\install_vbcable.ps1"

  ExecWait '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\install_vbcable.ps1" -CheckOnly' $0
  ${If} $0 == 0
    Goto vbcable_ready
  ${EndIf}

  IfSilent vbcable_no_ui
  ${If} $PassiveMode = 1
    Goto vbcable_no_ui
  ${EndIf}

  MessageBox MB_OKCANCEL|MB_ICONQUESTION "O VoxCraft exige o VB-Audio Virtual Cable para funcionar. Clique em OK para baixar e instalar o driver e autorizar a solicitação de administrador do Windows. Cancelar interrompe a instalação do VoxCraft.$\r$\n$\r$\nVoxCraft requires VB-Audio Virtual Cable. Click OK to download and install the driver and approve the Windows administrator prompt. Cancel aborts VoxCraft installation." IDOK vbcable_install
  Abort "VB-Audio Virtual Cable is required."

vbcable_install:
  ExecWait '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\install_vbcable.ps1"' $0
  ${If} $0 != 0
    MessageBox MB_OK|MB_ICONSTOP "O VB-Audio Virtual Cable não foi instalado. A instalação do VoxCraft será interrompida.$\r$\n$\r$\nVB-Audio Virtual Cable was not installed. VoxCraft installation will stop."
    Abort "VB-Audio Virtual Cable installation failed."
  ${EndIf}
  Goto vbcable_ready

vbcable_no_ui:
  Abort "VB-Audio Virtual Cable is required. Run the installer interactively."

vbcable_ready:
!macroend
