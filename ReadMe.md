GeoSpatial Analysis

Compare the real cost of living across US cities — not just rent, but income, purchasing power, walkability, and available properties.**


What it does:
Most cost-of-living tools give you one number. LiveIndex gives you the full picture — what people actually earn in a city, how far that income goes, what it costs to rent or buy, and how walkable the neighborhood is. All in one interactive map.



**DISCLAIMER**
This version of the application is HEAVILY limited on coverage from the free tier API rate limits
This means the application is capable of more, but you need to pay for its full capabilities


- Click any city on the map to see its full profile
- Compare up to 4 cities side by side
- Browse real property listings filtered by rental vs. for-sale and residential vs. commercial
- Track rent and home value trends over 1, 2, or 5 years

Data sources

| Source | Data | Frequency |
|--------|------|-----------|
| [US Census Bureau ACS](https://www.census.gov/data/developers/data-sets/acs-1year.html) | Median household income | Annual |
| [Bureau of Labor Statistics](https://www.bls.gov/developers/) | Regional Price Parity index | Annual |
| [Zillow Research](https://www.zillow.com/research/data/) | Median rent, home values, trends | Monthly |
| [OpenStreetMap Overpass API](https://overpass-api.de) | Walk, transit, and bike scores | Weekly |
| [Rentcast](https://rentcast.io/api) | Active property listings | On demand, cached 7 days |

Stack

| Layer | Technology |
|-------|------------|
| Data pipeline | Python, pandas, requests, APScheduler |
| Database | PostgreSQL |
| API | FastAPI, asyncpg, httpx |
| Frontend | React, Leaflet, Recharts |
| Infrastructure | Docker, Docker Compose |
| Deployment | Vercel (frontend), Railway (API + DB) |

Architecture

The pipeline runs on a weekly cron schedule. Zillow data refreshes every Monday to catch their monthly CSV updates. Property listings from Rentcast are fetched on demand and cached in Postgres for 7 days to stay within free tier limits.

Prerequisites

- Docker + Docker Compose
- Node.js 18+
- API keys: [Census Bureau](https://api.census.gov/data/key_signup.html) (free) and [Rentcast](https://app.rentcast.io) (free tier)

Setup

Create your env file
cp .env.example .env
Fill in CENSUS_API_KEY and RENTCAST_API_KEY in .env

Start the backend
docker compose up --build

Seed the database (new terminal)
docker compose run --rm scheduler python scheduler.py --run-now --source census
docker compose run --rm scheduler python scheduler.py --run-now --source zillow

Start the frontend (new terminal)
cd frontend
npm install
npm start
```

The app will be running at `http://localhost:3000` and the API at `http://localhost:8000`.

Environment variables

```env
CENSUS_API_KEY=           # Required — census.gov API key
RENTCAST_API_KEY=         # Required — rentcast.io API key
DATABASE_URL=postgresql://postgres:localdev@db:5432/liveindex
POSTGRES_PASSWORD=localdev
BLS_API_KEY=              # Optional — increases BLS rate limits
APP_ENV=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
PIPELINE_ALERT_URL=       # Optional — Slack webhook for pipeline failure alerts
```
API reference

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/cities` | All tracked metros with core metrics |
| `GET /api/v1/cities/{fips}` | Full profile for one city |
| `GET /api/v1/compare?ids=35620,12420` | Side-by-side comparison of 2–4 cities |
| `GET /api/v1/trends/{fips}` | Rent and home value time series |
| `GET /api/v1/map` | GeoJSON for the map layer |
| `GET /api/v1/listings/{fips}` | Active property listings |
| `GET /health` | Liveness check |
| `GET /status` | DB status and last pipeline run |

Full interactive docs at `/docs` when running locally.

Cities covered
New York, Los Angeles, Chicago, Austin, Denver, Nashville, Phoenix, Seattle.

To add more cities, update the `METROS` list in `backend/app/ingest.py` and `clean.py` with the city's FIPS code, BLS area code, Zillow region name, and lat/lon.

Roadmap

- [ ] Add more cities
- [ ] School district ratings overlay
- [ ] Crime index per metro (FBI UCR data)
- [ ] Salary-adjusted comparison (enter your income, see it mapped to each city)
- [ ] Mobile-optimized layout

---

License

MIT
