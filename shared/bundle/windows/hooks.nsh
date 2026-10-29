; GUStay NSIS hooks.
;
; The Tauri installer already writes the .gustay association through the
; APP_ASSOCIATE macro. These hooks only tell Explorer that the association
; table changed, so the new icon and "Open with" entry are visible without
; restarting Explorer.
;
; SHCNE_ASSOCCHANGED = 0x08000000, SHCNF_IDLIST = 0.

!macro NSIS_HOOK_POSTINSTALL
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
!macroend
