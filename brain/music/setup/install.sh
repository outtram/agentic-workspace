#!/bin/bash
# TidalCycles full stack installer for macOS
# Installs: SuperCollider, Haskell (GHC + Cabal), TidalCycles, SuperDirt
#
# Usage: bash brain/music/setup/install.sh
# Safe to run multiple times (idempotent).

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No colour

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
step() { echo -e "\n${YELLOW}→${NC} $1"; }

echo "╔══════════════════════════════════════╗"
echo "║   TidalCycles Stack Installer        ║"
echo "║   macOS — idempotent                 ║"
echo "╚══════════════════════════════════════╝"

# --- 1. Homebrew ---
step "Checking Homebrew..."
if command -v brew &>/dev/null; then
    ok "Homebrew already installed"
else
    warn "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ok "Homebrew installed"
fi

# --- 2. SuperCollider ---
step "Checking SuperCollider..."
if [ -d "/Applications/SuperCollider.app" ]; then
    ok "SuperCollider already installed"
else
    warn "Installing SuperCollider via Homebrew..."
    brew install --cask supercollider
    ok "SuperCollider installed"
fi

# --- 3. Haskell toolchain (GHC + Cabal) ---
step "Checking GHC (Haskell compiler)..."
if command -v ghc &>/dev/null; then
    ok "GHC already installed ($(ghc --version | head -1))"
else
    warn "Installing GHC and Cabal..."
    brew install ghc cabal-install
    ok "GHC and Cabal installed"
fi

# --- 4. Cabal update ---
step "Updating Cabal package index..."
cabal update
ok "Cabal index updated"

# --- 5. TidalCycles ---
step "Checking TidalCycles..."
if ghc-pkg list tidal 2>/dev/null | grep -q tidal; then
    ok "TidalCycles already installed"
else
    warn "Installing TidalCycles (this takes a few minutes)..."
    cabal install tidal --lib
    ok "TidalCycles installed"
fi

# --- 6. SuperDirt (SuperCollider quark) ---
step "Installing SuperDirt quark..."
if command -v sclang &>/dev/null; then
    echo 'Quarks.install("SuperDirt"); 0.exit' | sclang 2>/dev/null || true
    ok "SuperDirt quark installed (or already present)"
else
    # sclang might not be on PATH — try the app bundle
    SCLANG="/Applications/SuperCollider.app/Contents/MacOS/sclang"
    if [ -f "$SCLANG" ]; then
        echo 'Quarks.install("SuperDirt"); 0.exit' | "$SCLANG" 2>/dev/null || true
        ok "SuperDirt quark installed (or already present)"
    else
        warn "Could not find sclang — install SuperDirt manually from SuperCollider IDE"
        warn "In SuperCollider, run: Quarks.install(\"SuperDirt\")"
    fi
fi

# --- Summary ---
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Installation Complete!             ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Installed:"
command -v ghc &>/dev/null && ok "GHC $(ghc --numeric-version)" || warn "GHC not found"
command -v cabal &>/dev/null && ok "Cabal $(cabal --numeric-version)" || warn "Cabal not found"
[ -d "/Applications/SuperCollider.app" ] && ok "SuperCollider" || warn "SuperCollider not found"
ghc-pkg list tidal 2>/dev/null | grep -q tidal && ok "TidalCycles" || warn "TidalCycles not found"

echo ""
echo "Next steps:"
echo "  1. Open SuperCollider and run: SuperDirt.start"
echo "  2. In Command Centre, press 'm' to enter music mode"
echo "  3. Type what you want to hear!"
echo ""
