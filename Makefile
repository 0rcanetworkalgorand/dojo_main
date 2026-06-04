.PHONY: setup dev stop

# ─── Setup: install dependencies and run database migrations ───────────────────
setup:
	@echo "📦 Installing backend dependencies..."
	cd dojo-backend && npm install
	@echo "🗄️  Running Prisma generate and migrate..."
	cd dojo-backend && npx prisma generate && npx prisma migrate dev
	@echo "📦 Installing frontend dependencies..."
	cd dojo-frontend && npm install
	@echo "✅ Setup complete."

# ─── Dev: start backend and frontend, poll for readiness ──────────────────────
dev:
	@echo "🚀 Starting backend on port 3001..."
	cd dojo-backend && npm run dev &
	@echo "🚀 Starting frontend on port 3000..."
	cd dojo-frontend && npm run dev &
	@echo "⏳ Waiting for backend (http://localhost:3001)..."
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:3001 > /dev/null 2>&1; then \
			echo "✅ Backend is ready."; \
			break; \
		fi; \
		if [ $$i -eq 30 ]; then \
			echo "❌ Backend failed to start within 30 seconds."; \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@echo "⏳ Waiting for frontend (http://localhost:3000)..."
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:3000 > /dev/null 2>&1; then \
			echo "✅ Frontend is ready."; \
			break; \
		fi; \
		if [ $$i -eq 30 ]; then \
			echo "❌ Frontend failed to start within 30 seconds."; \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@echo ""
	@echo "════════════════════════════════════════════"
	@echo "  🎉 All services running!"
	@echo "  Backend:  http://localhost:3001"
	@echo "  Frontend: http://localhost:3000"
	@echo "════════════════════════════════════════════"

# ─── Stop: kill processes on ports 3000 and 3001 ──────────────────────────────
stop:
	@echo "🛑 Stopping services..."
	-@lsof -ti:3001 | xargs kill 2>/dev/null || true
	-@lsof -ti:3000 | xargs kill 2>/dev/null || true
	@echo "✅ Services stopped."
