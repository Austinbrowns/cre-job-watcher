# CRE Signal — Commercial Real Estate Analyst Job Watcher

CRE Signal is a daily job-market watcher built for the Financial Data Analytics project in the attached brief. It monitors public, no-login applicant-tracking-system feeds for commercial real estate, real estate finance, development, property management, and related analyst roles.

The repository is designed for GitHub Actions and GitHub Pages. The pipeline stores compressed raw responses, rebuilds a deterministic history file from raw files alone, updates a daily GitHub Issue, and publishes a three-page installable site.

## Watchlist and APIs

Every source is a public JSON GET endpoint. The pipeline never reads the HTML of a careers page.

| Source | Employer | ATS | Public feed |
| --- | --- | --- | --- |
| `crexi` | Crexi | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/crexi/jobs?content=true` |
| `northmarq` | Northmarq | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/northmarq/jobs?content=true` |
| `sands_investment_group` | Sands Investment Group | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/sandsinvestmentgroup/jobs?content=true` |
| `flexential` | Flexential | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/flexentialcorp/jobs?content=true` |
| `centennial` | Centennial Real Estate Company | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/centennial/jobs?content=true` |
| `pma` | Property Management Associates | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/propertymanagementassociates/jobs?content=true` |
| `tpg` | TPG | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/tpgcareers/jobs?content=true` |
| `pretium` | Pretium | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/pretiumpartnersllc/jobs?content=true` |
| `rebuilt` | Rebuilt | Greenhouse | `https://boards-api.greenhouse.io/v1/boards/rebuilt/jobs?content=true` |
| `nai_norcal` | NAI Northern California | Lever | `https://api.lever.co/v0/postings/nainnorcal?mode=json` |
| `beedie` | Beedie | Lever | `https://api.lever.co/v0/postings/beedie?mode=json` |
| `flow` | Flow | Lever | `https://api.lever.co/v0/postings/flowlife?mode=json` |
| `eq_bank` | EQ Bank | Lever | `https://api.lever.co/v0/postings/eqbank?mode=json` |
| `colliers` | Colliers | SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/Colliers/postings?limit=100&offset=0&destination=PUBLIC` |
| `turner_townsend` | Turner & Townsend | SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/TurnerTownsend/postings?limit=100&offset=0&destination=PUBLIC` |
| `svn_lord_partners` | SVN Lord Partners | SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/SVNLordPartners/postings?limit=100&offset=0&destination=PUBLIC` |

SmartRecruiters sources are paginated automatically. If a board ever returns more than 5,000 postings, add a public query such as `q=analyst` to that source in `watcher/config.py` and document it here.

## Title rule

`in_role` is true when the title contains one of these terms and does not contain an excluded technology, HR, marketing, or security term:

```text
analyst, analytics, research, underwriting, valuation, acquisitions,
asset management, portfolio management, capital markets, real estate finance,
market intelligence, investment analyst
```

The pipeline keeps every posting returned by every source. The rule only controls the `in_role` flag and the default Browse view.

## Data files

- `data/raw/<UTC date>/<source>.json.gz` — exact successful source responses, compressed.
- `data/history.csv` — one row per posting, rebuilt from raw files alone.
- `data/status.json` — latest run time, counts, source health, and successful-day count.
- `data/runs.jsonl` — one audit record per pipeline run, including source failures.

The history columns are the required columns from the brief: `posting_id`, `source`, `source_id`, `employer`, `title`, `location`, `department`, `posted_date`, `url`, `in_role`, `first_run`, `first_seen`, `last_seen`, `status`, and `removed_date`.

## Repository file map

- `watcher/config.py` — 16-employer ATS configuration and endpoint construction.
- `watcher/sources.py` — JSON fetchers, SmartRecruiters pagination, and source normalizers.
- `watcher/title_rules.py` — the CRE analyst title rule.
- `watcher/history.py` — deterministic raw-file-to-history builder and daily change logic.
- `watcher/status.py` — status-file calculations.
- `watcher/github.py` — daily Issue creation, update, and closing logic.
- `watcher/pipeline.py` — end-to-end daily pipeline and optional Git commit/push.
- `watcher/__init__.py` — package metadata.
- `tests/fixtures/*.json` — representative Greenhouse, Lever, and SmartRecruiters responses.
- `tests/test_sources.py` — conversion tests for every ATS type.
- `tests/test_title_rule.py` — title-rule tests.
- `tests/test_history.py` — first-seen, last-seen, removal, and reopening tests.
- `index.html` — Today page.
- `browse.html` — Browse page with filters and browser shortlist.
- `market.html` — client-side six-section Market report.
- `app.js` — browser data loading, CSV parsing, calculations, and interactions.
- `styles.css` — shared responsive visual system.
- `manifest.webmanifest`, `service-worker.js`, `icon.svg` — installable/offline web-app files.
- `.github/workflows/tests.yml` — pytest on every push and pull request.
- `.github/workflows/daily.yml` — scheduled fetch, Issue, commit, and Pages deployment.
- `.github/workflows/pages.yml` — Pages deployment for normal `main` branch pushes.
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt` — Python project and test configuration.
- `.gitignore` — excludes local caches while preserving raw data.
- `submission.txt` — four-line submission template to complete before turning in.

## Run locally

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m watcher.pipeline --no-issues
python -m http.server 8000
```

Open `http://localhost:8000/index.html`. A live run needs internet access; tests use local fixtures and do not call employers.

The history builder is deterministic and can be run directly by importing `watcher.history.build_history`. The pipeline itself rebuilds `data/history.csv` after every fetch, so changing the title rule applies to all stored days.

## GitHub setup

1. Create a public GitHub repository from this folder and push the `main` branch.
2. In repository Settings → Actions → General, allow GitHub Actions to read and write repository contents.
3. In Settings → Pages, choose GitHub Actions as the source.
4. The daily workflow runs once per day, creates or updates the date-titled Issue, closes older daily Issues, commits the raw/history/status files, and deploys the site.
5. The tests workflow runs on every push and pull request.

The GitHub Actions token is used only for the repository’s Issue and commit operations. ATS feeds require no login or API key.

## Optional CRE analyst datasets

These are deliberately separate from the job watcher because they are market-data sources, not employer job-board feeds:

- Census ACS and Economic Census — demographics, income, employment, and business activity.
- BLS QCEW — employment and wages by county and NAICS industry.
- FHFA Multifamily Public Use Database — multifamily mortgage and property characteristics.
- SEC EDGAR XBRL APIs — public REIT financial statements and company facts.

They are useful future portfolio extensions for market-selection or REIT analysis, but they do not replace the 15 ATS sources required by this assignment.
