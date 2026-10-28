# CineBook frontend

Responsive React + Vite frontend for discovering movies, major events, and local experiences.

## Run locally
From the repository root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Vite prints the local URL (normally http://localhost:5173). The API base URL defaults to `http://127.0.0.1:8000`; change `VITE_API_BASE_URL` for another backend.

## Features
- Responsive discovery page with search, city filtering, categories, event type filters, and saved listings.
- Pulls cities, movies, published events, and sessions from the FastAPI API.
- Registration and sign-in using backend auth endpoints; access token is stored in local browser storage.
- Live session selection, seat selection for cinema shows, general-admission ticket selection for events, and booking history in the API.
- Checkout creates a demo payment record only. No real payment gateway or card details are involved.
- Clearly labelled preview cards keep the page viewable when there are no published records or the API is offline. Preview listings cannot be booked.

## Run the full app
Start the backend first from the `backend/` folder, then run this frontend in a second terminal. Keep the backend running while using the site.
