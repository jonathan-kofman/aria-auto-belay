# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

ARIA is a hybrid mechanical + AI-assisted lead climbing auto belay device. The codebase has three software products:

1. **Streamlit Dashboard** (`aria_dashboard.py`) — virtual physics testing, state machine simulation, PID tuning
2. **React Native App** (`aria-climb/`) — Expo-based mobile app (requires Firebase + native build)
3. **Firmware** (`firmware/`) — STM32 + ESP32 C++/Arduino (requires hardware to flash)

In the current development phase (pre-hardware), the dashboard and Python CLI tools are the primary development surfaces.

### Running the dashboard

```bash
streamlit run aria_dashboard.py --server.port 8501 --server.headless true
```

Runs on `http://localhost:8501`. Uses `aria_models/` for physics/state-machine logic.

### Running the CLI simulator

```bash
python3 tools/aria_simulator.py
```

Interactive REPL — type `help` for commands, `scenario climb` for a full climb walkthrough.

### React Native app (`aria-climb/`)

- Install: `npm install --legacy-peer-deps` (required due to Victory Native / React 18 peer dep conflicts)
- Requires Firebase native config (`google-services.json` / `GoogleService-Info.plist`) to run
- Cannot use Expo Go; needs `expo-dev-client` native build (`npx expo run:android` or `npx expo run:ios`)
- Pre-existing TypeScript errors exist in `npx tsc --noEmit` — these are in the repo, not from setup
- No ESLint or Prettier config is set up in the project

### Linting / type-checking

- **Python**: No linter config (no flake8, pyproject.toml, etc.). Use `python3 -m py_compile <file>` for syntax checks.
- **TypeScript (aria-climb)**: `npx tsc --noEmit` in `aria-climb/`. Has pre-existing type errors.
- No project-wide lint or test scripts are configured.

### Key constants rule

Every constant in `tools/aria_simulator.py` must match `firmware/stm32/aria_main.cpp`. See `CURSOR_GUIDE.md` for details.
