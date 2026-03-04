# ENGRAM — AI LinkedIn Machine

> Last updated: 2026-03-04 (Dashboard build session)

## Current State: Dashboard webapp Phase 1+2 COMPLETE — needs build verification

## Completed Work (2026-03-04)

### FastAPI Backend (api/) — DONE
- Added CRUD methods to `sheets/client.py`: update_engine_control, get_tab_data, append_tab_row, update_tab_row, delete_tab_row, get_system_log, update_schedule_config
- `api/server.py` — FastAPI app, CORS, all routes at /api
- `api/deps.py` — SheetsClient singleton, API key auth
- 10 route modules: engine, schedule, content, targets, templates, rules, personas, analytics, history, alerts
- 2 services: alert_service (AlertManager w/ urgency timers), analytics_service (aggregates tracker+SystemLog)

### Next.js Dashboard (dashboard/) — DONE
- Next.js + shadcn/ui + Tailwind dark mode + recharts + lucide-react
- `src/lib/api.ts` — typed API client, `src/lib/websocket.ts` — WS client
- `src/hooks/use-api.ts`, `src/hooks/use-alerts.ts`
- Layout with sidebar (12 nav items)
- 11 pages: /, /alerts, /analytics, /history, /config/{engine,schedule,content,targets,templates,rules,personas}

### Docker — DONE
- Dockerfile.api, dashboard/Dockerfile, docker-compose.yml

## Next Steps
1. `pip install fastapi uvicorn[standard] websockets` in project venv
2. `python -m api.server` → test `curl localhost:8000/api/health`
3. `cd dashboard && npm run build` → fix any TS errors
4. Add .env vars: DASHBOARD_API_KEY, CORS_ORIGINS, NEXT_PUBLIC_API_URL
5. `docker-compose up --build` → verify both containers
6. Add create/edit forms to config pages (most are read+delete only)
7. Phase 3: Deploy to Hetzner/Coolify
