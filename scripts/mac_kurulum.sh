#!/usr/bin/env bash
# ============================================================
# Claude Code Mac Kurulum — bypass/sudo/managed-settings'e DOKUNMAZ
# ============================================================
# Yapar:
#  1) ~/.claude/settings.json yedekle + yaz (model=opus-4-8, effort=high,
#     co-author/PR attribution KAPALI, autoUpdates=stable)
#  2) iCloud yedek dizini olustur
#  3) ~/.claude/bin/icloud-backup.sh yaz (~/.claude -> iCloud, rsync -a --delete)
#  4) LaunchAgent (her 30dk + boot) yukle ve bir kere calistir
#  5) `claude update` cagir (opus-4-8 icin v2.1.154+)
#  6) Bitince iCloud projects klasorunu VS Code'da ac
#
# DOKUNULMAZ: bypass mode, sudo, managed-settings (kullanici elinde)
# DOKUNULMAZ: DISABLE_TELEMETRY (1M context + Remote Control icin sart)
# DOKUNULMAZ: git remote eklemek (Github disarida, attribution kapali)
# ============================================================
set -euo pipefail

# ── 1) settings.json yaz ─────────────────────────────────────
SETTINGS="$HOME/.claude/settings.json"
mkdir -p "$HOME/.claude"
if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d_%H%M%S)"
  echo "✅ Eski settings yedeklendi"
fi
cat > "$SETTINGS" <<'JSON'
{
  "model": "claude-opus-4-8",
  "effort": "high",
  "attribution": { "commit": "", "pr": "" },
  "autoUpdatesChannel": "stable"
}
JSON
echo "✅ ~/.claude/settings.json yazildi (model=opus-4-8, effort=high)"

# ── 2) iCloud yedek dizinleri ────────────────────────────────
ICLOUD="$HOME/Library/Mobile Documents/com~apple~CloudDocs/ClaudeCode"
mkdir -p "$ICLOUD/config" "$ICLOUD/projects"
echo "✅ iCloud yedek dizinleri hazir: $ICLOUD"

# ── 3) iCloud backup script ──────────────────────────────────
mkdir -p "$HOME/.claude/bin"
BACKUP="$HOME/.claude/bin/icloud-backup.sh"
cat > "$BACKUP" <<'SH'
#!/usr/bin/env bash
set -uo pipefail
SRC="$HOME/.claude/"
DST="$HOME/Library/Mobile Documents/com~apple~CloudDocs/ClaudeCode/config/"
# Sik degisen / gereksiz olanlari at: bin (run-time), statsig, shell-snapshots, *.log, *.lock, node_modules
rsync -a --delete \
  --exclude 'bin' --exclude 'statsig' --exclude 'shell-snapshots' \
  --exclude '*.log' --exclude '*.lock' --exclude 'node_modules' \
  "$SRC" "$DST"
SH
chmod +x "$BACKUP"
echo "✅ icloud-backup.sh yazildi (rsync, exclude'lar dahil)"

# ── 4) LaunchAgent ───────────────────────────────────────────
PLIST="$HOME/Library/LaunchAgents/net.miknatis.claudecode.icloudbackup.plist"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>net.miknatis.claudecode.icloudbackup</string>
  <key>ProgramArguments</key>
  <array>
    <string>$BACKUP</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>1800</integer>
  <key>StandardOutPath</key>
  <string>$HOME/.claude/icloud-backup.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/.claude/icloud-backup.err</string>
</dict>
</plist>
EOF
# Yeniden yukle (varsa unload, sonra load + start)
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"
launchctl start net.miknatis.claudecode.icloudbackup 2>/dev/null || true
echo "✅ LaunchAgent yuklendi (RunAtLoad + her 30dk) + bir kez calistirildi"

# ── 5) claude update ─────────────────────────────────────────
if command -v claude >/dev/null 2>&1; then
  echo "→ claude update calistiriliyor..."
  claude update || echo "⚠️ claude update basarisiz (manuel: 'claude update')"
else
  echo "⚠️ 'claude' komutu PATH'te yok. Manuel: npm install -g @anthropic-ai/claude-code"
fi

# ── 6) VS Code ile iCloud projects'i ac (opsiyonel) ──────────
if command -v code >/dev/null 2>&1; then
  echo "→ VS Code ile $ICLOUD/projects aciliyor..."
  code "$ICLOUD/projects" || true
else
  echo "ℹ️ VS Code CLI yok. Manuel: code \"$ICLOUD/projects\""
fi

echo ""
echo "🦅 KURULUM TAMAM"
echo "   settings    : $SETTINGS"
echo "   backup      : $BACKUP"
echo "   launchagent : $PLIST"
echo "   iCloud      : $ICLOUD"
echo ""
echo "Bir sonraki adim: yeni Claude Code oturumu ac → 4.8 + 1M context aktif olmali."
echo "Bypass (kullanici karari): yeni oturumu 'claude --permission-mode bypassPermissions' ile baslat."
