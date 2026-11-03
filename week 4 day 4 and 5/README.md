# ReclaimAI

ReclaimAI is a lost-and-found application built with React, FastAPI, and PostgreSQL. It lets people publish lost and found reports, browse active public listings, review explainable matches, submit ownership claims, and record a completed return. Administrators review claims, manage categories, and moderate reports.

It uses a deterministic, versioned matching algorithm. It does not use a trained model or make ownership decisions.

## Requirements

- Windows 10/11
- Python 3.11 or newer
- Node.js 20.19+ or 22.12+
- PostgreSQL 15 or newer, running locally

## 1. Configure PostgreSQL and the backend

1. Start the installed PostgreSQL service. In PowerShell, check its installed service name:

   ```powershell
   Get-Service *postgres*
   ```

   If it is stopped, start the matching service from the Windows Services app or an elevated PowerShell window:

   ```powershell
   Start-Service postgresql-x64-16
   ```

   The service name may be different on your computer.

2. Create an empty database named `reclaimai_db` using pgAdmin or `psql`:

   ```sql
   CREATE DATABASE reclaimai_db;
   ```

3. Open PowerShell in `reclaimai\backend`, copy `.env.example` to `.env`, then edit `.env`:

   ```powershell
   Set-Location C:\projects\week4day4\reclaimai\backend
   Copy-Item .env.example .env
   ```

   Set `DATABASE_NAME`, `DATABASE_USER`, and `DATABASE_PASSWORD` to match PostgreSQL. Replace `JWT_SECRET_KEY` with a random value; for example, generate one with:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Set a strong `ADMIN_PASSWORD'.

4. Install Python dependencies, apply the database migrations, and seed the starter data:

   ```powershell
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   python -m scripts.seed_categories
   python -m scripts.seed_admin
   ```

   If this is a fresh Python setup without the included `venv`, create it first with `python -m venv venv`.

5. Start the API in this PowerShell window:

   ```powershell
   uvicorn app.main:app --reload
   ```

   Keep this window open. The API is at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

## 2. Configure and start the frontend

Open a second PowerShell window:

```powershell
Set-Location C:\projects\week4day4\reclaimai\frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Keep this window open and visit `http://localhost:5173`.

If you change the API address, set `VITE_API_BASE_URL` in `frontend\.env` and set `FRONTEND_URL` in `backend\.env` to the frontend origin. Restart both development servers after changing environment values.

## 3. Verify the setup

Open these URLs in a browser:

1. `http://127.0.0.1:8000/api/v1/health` — expect `{"status":"healthy", ...}`.
2. `http://127.0.0.1:8000/api/v1/health/database` — expect `status: healthy` and the configured database.
3. `http://127.0.0.1:8000/api/v1/health/schema` — expect `status: healthy` and eight required tables.
4. `http://127.0.0.1:8000/docs` — confirm the ReclaimAI API routes are listed.
5. `http://localhost:5173` — confirm the ReclaimAI home page opens.

The database and schema health checks require PostgreSQL to be running and migrations to have been applied.

## 4. Click-through demo: report → match → claim → return

Use three accounts: two ordinary users and the seeded administrator. Keep the answer to the found report’s private question; the claimant must enter it to submit a claim.

1. **Create the lost-item owner.** On the home page click **Create account**. Register a user such as Alice, then sign in.
2. **Submit a lost report.** Click **Report lost**. Choose **Bag** and enter:
   - Item name: `Laptop bag`
   - Colour / brand: `Black` / `Dell`
   - Date: today (or the day before the found report)
   - Area: `Block B Cafeteria`
   - Description: `Black bag, grey strap, front scratch, zipper`
   - Continue with **Review report**, then **Submit report**.
   The new report page should show its `RA-...` reference and matching status.
3. **Create the finder account.** Sign out and click **Create account** to register a second user, such as Bob. Sign in as Bob and click **Report found**.
4. **Submit the found report.** Choose **Bag** and enter:
   - Item name: `Laptop shoulder bag`
   - Colour / brand: `Black` / `Dell`
   - Date: the same day or one day after the lost report
   - Area: `Cafeteria, Block B`
   - Description: `Black bag with grey strap, front button and dent`
   - Verification question: `What is inside the front pocket?`
   - Verification answer: choose a private answer and remember it
   Review and submit. The rules engine should produce a high-scoring **STRONG** match for the sample data.
5. **Submit a claim as Alice.** Sign out, sign in as Alice, and open **My activity** → **Matches**. On the laptop-bag match click **Submit a claim**. Enter a specific ownership explanation and the answer Bob set. Click **Submit claim**. The claim should appear as **PENDING** under **My claims**.
6. **Review the claim as administrator.** Sign out. Sign in with `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `backend\.env`. Open **Admin** → **Claims**. Review the side-by-side report details and explanation. Enter a review note, then click **Start review** and **Approve** (approval requires a note).
7. **Record the handover.** As an administrator, click **Confirm return** on the approved claim; or sign in as Alice and use **My activity** → **My claims** → **Confirm handover**. The claim becomes **COMPLETED**, Alice’s lost report becomes **RECOVERED**, and Bob’s found report becomes **RETURNED**.
8. **Check the totals.** Open **My activity** as Alice to see the recovered item count. Sign in as the administrator and open **Admin** → **Overview** to see updated system counts and recent activity.

Other useful screens:

- **Browse reports** supports type, category, colour, brand, area, date, and text filters.
- A report owner can open a report to view its matches, edit it while active, or withdraw it with a reason.
- **Admin** → **Reports** supports moderation; **Admin** → **Categories** supports adding and activating/deactivating categories.
- Public report pages omit exact location, storage instructions, and verification questions/answers. The claim flow reveals only the question to the owner of the matching lost report.

## 5. Run checks

Backend matching regression tests:

```powershell
Set-Location C:\projects\week4day4\reclaimai\backend
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Frontend production build:

```powershell
Set-Location C:\projects\week4day4\reclaimai\frontend
npm run build
```

## Troubleshooting

- **Database unavailable:** confirm PostgreSQL is running and `backend\.env` has the right database/user/password.
- **Schema incomplete:** from `backend`, run `alembic upgrade head`.
- **No categories in the report form:** run `python -m scripts.seed_categories`.
- **Admin sign-in fails:** run `python -m scripts.seed_admin`, then sign in with the `ADMIN_EMAIL` and `ADMIN_PASSWORD` configured in `.env`.
- **Browser CORS errors:** set `FRONTEND_URL=http://localhost:5173` in `backend\.env`, then restart Uvicorn.
- **Report creation retry:** the app uses an idempotency key to prevent duplicate reports if the same submission is retried.

## Release 1 boundaries/future work

Direct image upload, maps/GPS, external AI services, chat, email/SMS notifications, payments, mobile clients, and automatic ownership decisions are not part of this release. Images are optional HTTP(S) URLs.
