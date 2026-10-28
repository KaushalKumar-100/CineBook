# CineBook frontend

React + Vite responsive discovery UI for movies, large events, and local events.

## Run locally
From the repository root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Vite prints the local URL (normally http://localhost:5173). The API base URL defaults to `http://127.0.0.1:8000`; change `VITE_API_BASE_URL` for another backend.

The frontend fetches live movies, published events, cities, and database health from the FastAPI service. When no published records exist or the API is offline, it uses clearly labelled preview cards so the page remains viewable. Preview listings do not create real bookings. Booking/auth APIs are available via the backend Swagger documentation; interactive sign-in and checkout screens are not yet integrated into this first frontend pass.
