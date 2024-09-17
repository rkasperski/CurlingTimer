# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

hiddenimports = ["zeroconf",
                 "zeroconf._utils.__init__", 
                 "zeroconf._utils.asyncio",
                 "zeroconf._utils.ipaddress",
                 "zeroconf._utils.name",
                 "zeroconf._utils.net",
                 "zeroconf._utils.time",
                 "zeroconf._handlers.answers",
                 "zeroconf._handlers.__init__",
                 "zeroconf._handlers.answers",
                 "zeroconf._handlers.multicast_outgoing_queue",
                 "zeroconf._handlers.query_handler",
                 "zeroconf._handlers.record_manager"
                 ]

CurlingTimer_a = Analysis(['CurlingTimer.py'],
                          pathex=[],
                          binaries=[('fonts/*.ttf', 'fonts')],
                          datas=[('defaults/*.toml', 'defaults'),
                                 ('templates/*.html', 'templates'),
                                 ('templates/*.js', 'templates'),
                                 ('templates/*.css', 'templates'),
                                 ('static/font/*', 'static/font'),
                                 ('static/font/fonts/*', 'static/font/fonts'),
                                 ('static/css/*', 'static/css'),
                                 ('static/js/*', 'static/js'),
                                 ('static/images/*', 'static/images'),
                                 ('info/*', 'info'),
                                 ('install/*', 'install'),
                                 ('install/systemd', 'install/systemd'),
                                 ("dist/cc_hwclock", "install")],
                          hiddenimports=hiddenimports,
                          hookspath=[],
                          hooksconfig={},
                          runtime_hooks=[],
                          excludes=[],
                          win_no_prefer_redirects=False,
                          win_private_assemblies=False,
                          cipher=block_cipher,
                          noarchive=False)


CurlingTimer_pyz = PYZ(CurlingTimer_a.pure, CurlingTimer_a.zipped_data,
                       cipher=block_cipher)


CurlingTimer_exe = EXE(CurlingTimer_pyz,
                       CurlingTimer_a.scripts,
                       [],
                       exclude_binaries=True,
                       name='CurlingTimer',
                       debug=False,
                       bootloader_ignore_signals=False,
                       strip=False,
                       upx=True,
                       console=True,
                       disable_windowed_traceback=False,
                       target_arch=None,
                       codesign_identity=None,
                       entitlements_file=None)


BreakTimer_a = Analysis(['BreakTimer.py'],
                        pathex=[],
                        binaries=[],
                        datas=[('defaults/*.toml', 'defaults'),
                               ('templates/*.css', 'templates'),
                               ('templates/*.html', 'templates'),
                               ('templates/*.js', 'templates'),
                               ('static/css/*', 'static/css'),
                               ('static/js/*', 'static/js'),
                               ('static/images/*', 'static/images'),],
                        hiddenimports=hiddenimports,
                        hookspath=[],
                        hooksconfig={},
                        runtime_hooks=[],
                        excludes=[],
                        win_no_prefer_redirects=False,
                        win_private_assemblies=False,
                        cipher=block_cipher,
                        noarchive=False)

BreakTimer_pyz = PYZ(BreakTimer_a.pure, BreakTimer_a.zipped_data,
                     cipher=block_cipher)

BreakTimer_exe = EXE(BreakTimer_pyz,
                     BreakTimer_a.scripts,
                     [],
                     exclude_binaries=True,
                     name='BreakTimer',
                     debug=False,
                     bootloader_ignore_signals=False,
                     strip=False,
                     upx=True,
                     console=True,
                     disable_windowed_traceback=False,
                     target_arch=None,
                     codesign_identity=None,
                     entitlements_file=None)

coll = COLLECT(CurlingTimer_exe,
               CurlingTimer_a.binaries,
               CurlingTimer_a.zipfiles,
               CurlingTimer_a.datas,
               BreakTimer_exe,
               BreakTimer_a.binaries,
               BreakTimer_a.zipfiles,
               BreakTimer_a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='CurlingTimer')
