# Job Application Automation System — Full Project Documentation

## 1. Project Overview

This project is a Python-based automation system that streamlines the job application process. It scrapes job postings from URLs, matches them against user preferences, generates a tailored PDF resume, fills out application forms via browser automation, and tracks all applications in a CSV file.

**Supported platforms:** Generic job sites (any URL) and **Naukri.com** (with login, search, and one-click apply).

**Language:** Python 3.13
**Key Libraries:** Selenium, BeautifulSoup4, pandas, reportlab, webdriver-manager, sentence-transformers (optional)

---

## 2. Project Structure

```
job_apply/
├── main.py                 # Entry point & orchestrator
├── job_scraper.py          # Generic job scraping
├── resume_modifier.py      # Generates tailored PDF resumes
├── application_tracker.py  # Tracks applications in CSV
├── browser_automation.py   # Browser control & form filling
├── job_matcher.py          # Filters jobs by preference/relevance
├── naukri_scraper.py       # Naukri.com job scraping & search
├── naukri_automation.py    # Naukri.com apply & profile management
├── requirements.txt        # Python dependencies
├── setup.sh                # Environment setup script
├── README.md               # User-facing readme
├── PROJECT_DOCUMENTATION.md# This file
├── config.json             # (generated at first run) Bot configuration
├── personal_details.json   # (generated at first run) User profile data
├── job_applications.csv    # (generated at runtime) Application log
├── job_application.log     # Runtime log file
└── resumes/                # (generated) Directory for tailored resumes
```

---

## 3. Application Flow

### 3a. Generic Flow (any job site)

```
apply_for_job(url)  [auto-detects naukri.com URLs]
       │
       ▼
Step 1: JobScraper.scrape_job(url)
       │  → extracts title, company, location, description, requirements
       ▼
Step 2: JobMatcher.match_job(job_details)
       │  → filters by preferences (exact, fuzzy, keyword, semantic)
       ▼
Step 3: ResumeModifier.modify_resume(job_details, personal_details)
       │  → generates a customized PDF resume in resumes/
       ▼
Step 4: BrowserAutomation.fill_application(url, ...)
       │  → opens browser, finds apply button, fills form, uploads resume
       │  → asks user confirmation before submitting
       ▼
Step 5: ApplicationTracker.add_application(url, job_details)
       ▼
     Done
```

### 3b. Naukri.com Flow

```
User selects Naukri menu option
       │
       ▼
┌────────────────────┐
│ naukri_login()     │  (main.py → NaukriScraper.login)
│ email + password   │  OTP handled interactively
└──────┬─────────────┘
       │
       ├─── Option 6: Single URL ──► NaukriAutomation.apply_to_job(url)
       │
       ├─── Option 7: Search & Apply
       │       │
       │       ▼
       │    NaukriScraper.search_jobs(keywords, location, experience)
       │       │  → returns list of job cards
       │       ▼
       │    For each job:
       │       NaukriScraper.scrape_job(url)   → full details
       │       JobMatcher.match_job(details)   → filter
       │       NaukriAutomation.apply_to_job() → click Apply
       │           ├── handle chatbot questions
       │           ├── handle external-apply redirect
       │           └── verify success
       │       ApplicationTracker.add_application()
       │
       └─── Option 8: Update profile resume
               NaukriAutomation.update_profile_resume(path)
```

---

## 4. File-by-File Reference

---

### 4.1 `main.py` — Entry Point & Orchestrator

**Class: `JobApplicationBot`**

Coordinates all modules. Loads configuration, manages the interactive CLI loop, and drives the application pipeline for each job. Also initialises Naukri-specific modules (`NaukriScraper`, `NaukriAutomation`) with a shared browser session.

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self, config_file: str = "config.json")` | Initializes logging, loads config and personal details, instantiates all module classes including Naukri modules (`NaukriScraper`, `NaukriAutomation`). |
| `setup_logging` | `(self)` | Configures Python `logging` to write to both `job_application.log` and stdout. Format: `%(asctime)s - %(levelname)s - %(message)s`. |
| `load_config` | `(self, config_file: str) -> Dict` | Reads and returns a JSON config file. Shows an error popup if the file is missing. |
| `load_personal_details` | `(self) -> Dict` | Reads `personal_details.json` (path taken from config). Shows an error popup if missing. |
| `show_error_popup` | `(self, message: str)` | Prints a formatted error message to the console and pauses execution with `input()` until the user presses Enter. Used as a manual intervention point. |
| `_is_naukri_url` | `(self, url: str) -> bool` | Returns `True` if the URL contains `naukri.com`. Used by `apply_for_job` to auto-route. |
| `apply_for_job` | `(self, job_url: str) -> bool` | **Core pipeline.** Auto-detects Naukri URLs and routes them to `_apply_naukri_single`. For other sites: (1) scrapes, (2) matches, (3) generates resume, (4) fills form, (5) tracks. |
| `bulk_apply` | `(self, job_urls: List[str])` | Iterates over a list of URLs, calls `apply_for_job` for each, with a 2-second delay between applications for rate limiting. Prints a success summary. |
| `naukri_login` | `(self) -> bool` | Reads Naukri credentials from config (or prompts the user). Delegates to `NaukriScraper.login`. Uses `getpass` for password input when not in config. |
| `_apply_naukri_single` | `(self, job_url: str) -> bool` | Ensures the user is logged in to Naukri, then delegates to `NaukriAutomation.apply_to_job`. |
| `naukri_search_and_apply` | `(self)` | Interactive prompt that asks for keywords, location, experience, and max applications, then runs `NaukriAutomation.search_and_apply`. Falls back to config values for defaults. |
| `naukri_update_resume` | `(self)` | Prompts for a resume file path and uploads it to the Naukri profile via `NaukriAutomation.update_profile_resume`. |

**Module-level data:**

- `config_template` (dict): Default structure for `config.json`. Contains keys: `personal_details_file`, `preferred_jobs`, `excluded_companies`, `min_salary`, `preferred_locations`, `experience_level`, and **`naukri`** (Naukri-specific settings — see Section 5).
- `personal_details_template` (dict): Default structure for `personal_details.json`. Contains keys: `name`, `email`, `phone`, `location`, `linkedin`, `summary`, `core_skills`, `skills`, `experience` (list of dicts with `title`, `company`, `duration`, `bullets`), `education` (list of dicts).

**`__main__` block:**
- Creates `config.json` and `personal_details.json` from templates if they don't exist.
- Instantiates `JobApplicationBot`.
- Runs an interactive CLI menu loop with 9 options: (1) single apply, (2) bulk apply, (3) stats, (5) Naukri login, (6) Naukri single apply, (7) Naukri search & auto-apply, (8) Naukri update resume, (9) exit.

---

### 4.2 `job_scraper.py` — Job Detail Extraction

**Class: `JobScraper`**

Uses Selenium to load job posting pages and extract structured data. Employs a multi-strategy approach with CSS selectors, meta tags, and page text analysis as fallbacks.

**Dependency:** Imports `BrowserSetup` from `browser_automation.py` for driver creation.

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self)` | Sets `self.driver = None`. |
| `setup_driver` | `(self)` | Lazily creates a headless Chrome driver via `BrowserSetup.create_driver(headless=True)`. |
| `scrape_job` | `(self, job_url: str) -> Dict` | Main entry point. Loads the URL, waits 3s, then calls each `extract_*` method. Returns a dict with keys: `url`, `title`, `company`, `location`, `description`, `requirements`, `scraped_at`. Returns `{}` on failure. Logs detailed extraction results and warnings for missing fields. |
| `extract_job_title` | `(self) -> str` | Tries (in order): specific CSS selectors (e.g. `h1[data-testid="job-title"]`, `.job-title`), generic `<h1>` tags (filtering out non-title content), `og:title` meta tag, page title parsing (splitting on `\|`). Returns `"Unknown Title"` if all fail. |
| `extract_company_name` | `(self) -> str` | Tries: specific CSS selectors (`.company-name`, etc.), `<a>` tags with `company` in their href, `og:site_name` meta tag. Returns `"Unknown Company"` if all fail. |
| `extract_location` | `(self) -> str` | Tries: specific CSS selectors (`.location`, etc.), regex patterns on page text for "Remote", "City, State", "City State, XX". Returns `"Unknown Location"` if all fail. |
| `extract_job_description` | `(self) -> str` | Tries: specific CSS selectors (`#jobDescriptionText`, `.job-description`, etc.), largest text block containing job-related keywords (responsibility, requirement, etc.), fallback content area selectors (`main`, `.content`). Returns `"No description found"` if all fail. |
| `extract_requirements` | `(self) -> List[str]` | Scans the job description for a hardcoded list of technology/qualification keywords (python, java, javascript, react, etc.) and returns all matches as a list. |
| `_extract_with_selectors` | `(self, selectors: List[str], context: str) -> str` | Helper that iterates over CSS selectors, returns the text of the first matching non-empty element. Returns `"Not found"` if none match. |

---

### 4.3 `resume_modifier.py` — PDF Resume Generation

**Class: `ResumeModifier`**

Generates a customized PDF resume using `reportlab`. The resume content (summary, skills) is tailored to match the job requirements.

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self)` | Sets `self.base_resume_path = None`. |
| `modify_resume` | `(self, job_details: Dict, personal_details: Dict) -> str` | Creates the `resumes/` directory, generates a timestamped PDF filename (`resume_YYYYMMDD_HHMMSS.pdf`), calls `create_customized_resume`, and returns the output path. Returns `None` on failure. |
| `create_customized_resume` | `(self, job_details: Dict, personal_details: Dict, output_path: str)` | Builds a PDF with sections: **Header** (name, email, phone, location), **Professional Summary** (customized via `generate_customized_summary`), **Key Skills** (prioritized via `get_relevant_skills`), **Experience** (from personal details, up to 3 bullet points per role). Uses `reportlab.pdfgen.canvas` with `letter` page size. |
| `generate_customized_summary` | `(self, job_details: Dict, personal_details: Dict) -> str` | Constructs a summary string that incorporates the user's base summary, the top 3 job requirements, the target job title, and the user's core skills. |
| `get_relevant_skills` | `(self, job_details: Dict, personal_details: Dict) -> List[str]` | Returns a prioritized list of skills: first skills that match job requirements, then remaining skills up to a maximum of 10. |

---

### 4.4 `application_tracker.py` — Application Logging

**Class: `ApplicationTracker`**

Maintains a CSV-based log of all job applications using pandas.

**CSV columns:** `date_applied`, `job_title`, `company`, `location`, `job_url`, `status`, `notes`

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self, csv_file: str = 'job_applications.csv')` | Sets the CSV file path and loads existing data into a pandas DataFrame. |
| `load_existing_data` | `(self) -> pd.DataFrame` | Reads the CSV file. If it doesn't exist, returns an empty DataFrame with the predefined columns. |
| `add_application` | `(self, job_url: str, job_details: Dict)` | Appends a new row with the current timestamp, job title, company, location, URL, status `"Applied"`, and auto-generated notes listing the job requirements. Saves immediately. |
| `save_data` | `(self)` | Writes the DataFrame to the CSV file (no index). |
| `get_application_stats` | `(self) -> Dict` | Returns a dict with `total_applications`, `applications_this_week` (last 7 days), and `unique_companies`. |

---

### 4.5 `browser_automation.py` — Browser Control & Form Filling

Contains two classes: `BrowserSetup` (static utility) and `BrowserAutomation` (form interaction).

#### Class: `BrowserSetup`

Centralized Chrome/Chromium WebDriver factory. All other modules use this for driver creation.

| Method | Signature | Description |
|---|---|---|
| `create_driver` (static) | `(headless: bool = True) -> webdriver.Chrome` | Creates a Chrome driver pointed at `/usr/bin/chromium-browser`. Adds flags: `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`, `--disable-extensions`, `--disable-plugins`, `--disable-images`, and optionally `--headless`. Falls back to `webdriver-manager` if the system driver fails. |
| `create_interactive_driver` (static) | `() -> webdriver.Chrome` | Same as above but **without** headless mode and without disabling images/plugins — designed for visible form filling where the user can observe the browser. |

#### Class: `BrowserAutomation`

Drives the actual form-filling workflow. Uses intelligent page analysis to find elements dynamically rather than relying on fixed selectors.

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self)` | Sets `self.driver = None`, `self.wait = None`. |
| `setup_driver` | `(self)` | Lazily creates an interactive driver via `BrowserSetup.create_interactive_driver()`, sets a `WebDriverWait` of 10 seconds. |
| `analyze_page_content` | `(self) -> Dict` | Scans the current page and returns a dict with keys: `apply_buttons`, `form_fields`, `file_uploads`, `submit_buttons`, `interactive_elements`. Each entry is a list of dicts describing found elements with confidence scores and identified types. |
| `_calculate_apply_confidence` | `(self, text, class_name, id_attr) -> float` | Heuristic scoring (0.0–1.0) for how likely an element is an "Apply" button based on its text and attributes. |
| `_calculate_submit_confidence` | `(self, text, class_name, id_attr) -> float` | Heuristic scoring (0.0–1.0) for how likely an element is a "Submit" button. |
| `_identify_form_field_type` | `(self, name, id_attr, placeholder, input_type) -> str` | Classifies a form field as `email`, `phone`, `name`, `linkedin`, `cover_letter`, or `unknown` based on its attributes. |
| `_identify_file_field_type` | `(self, name, id_attr, placeholder) -> str` | Classifies a file input as `resume`, `cover_letter`, or generic `file`. |
| `fill_application` | `(self, job_url, job_details, personal_details, resume_path) -> bool` | **Main form-filling pipeline.** Navigates to the URL, dismisses overlays, finds and clicks the apply button (with JS click fallback), fills form fields, and submits. Returns `True` on success. |
| `find_apply_button` | `(self)` | Multi-strategy search: (1) CSS selectors for common apply button patterns, (2) XPath text-based search (case-insensitive), (3) page content analysis picking highest confidence, (4) searching inside iframes. Returns the element or `None`. |
| `fill_form_fields` | `(self, personal_details, resume_path) -> bool` | Uses `analyze_page_content()` to identify fields, fills them with matching personal details (email, phone, name, linkedin), uploads resume to file inputs. Falls back to a traditional name/id-based mapping if analysis finds nothing. Prints a summary of filled fields and uploaded files. |
| `fill_field_by_name_or_id` | `(self, field_name, value) -> bool` | Fallback method that tries `input[name=...]`, `input[id=...]`, `input[data-testid=...]`, and `textarea` variants. |
| `_confirm_and_click` | `(self, element) -> bool` | Prompts the user in the terminal for confirmation before clicking a submit button. Returns `False` if the user types `n`. |
| `find_resume_upload` | `(self)` | Fallback method to find a file input for resume upload via selectors like `input[type="file"]`, `input[accept*=".pdf"]`, `input[name*="resume"]`. |
| `submit_application` | `(self) -> bool` | Finds the submit button via (1) CSS selectors, (2) XPath text search, (3) page analysis with highest confidence. Always calls `_confirm_and_click` before submitting. |
| `_dismiss_overlays` | `(self)` | Attempts to close cookie banners, modals, and popups by clicking common dismiss selectors (OneTrust, generic `.close`, `[data-dismiss="modal"]`, etc.), then sends Escape key as a last resort. |

---

### 4.6 `job_matcher.py` — Job Filtering & Relevance Scoring

**Class: `JobMatcher`**

Determines whether a scraped job is a good fit using a multi-strategy weighted scoring system. Optionally uses `sentence-transformers` for semantic similarity.

**Excluded keywords (hardcoded):** `unpaid`, `intern`, `volunteer`, `internship`

**Keyword variations map:** Maps terms like `software engineer` → `[software, engineer, developer, programmer, swe]`, `frontend` → `[front-end, front end, fe, ui, user interface]`, etc.

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self, preferred_jobs: List[str])` | Stores lowercased preferred job titles, initializes keyword variations, and loads the `all-MiniLM-L6-v2` SentenceTransformer model if available. |
| `match_job` | `(self, job_details: Dict) -> bool` | Public interface, delegates to `is_suitable_job`. |
| `is_suitable_job` | `(self, job_details: Dict) -> bool` | Computes a weighted score from four strategies: exact match (weight 1.0), fuzzy match (0.8), keyword variations (0.7), semantic similarity (0.6). Accepts the job if the weighted score ≥ 0.6 threshold. Logs detailed per-strategy scores. If no preferences are set, accepts all jobs that don't contain excluded keywords. |
| `_has_excluded_keywords` | `(self, title, description) -> bool` | Returns `True` if any excluded keyword is found in the title or description. |
| `_exact_match_score` | `(self, title, description) -> float` | Fraction of preferred job keywords found exactly in the text. |
| `_fuzzy_match_score` | `(self, title, description) -> float` | Uses `difflib.SequenceMatcher` to find the best fuzzy match (>70% similarity) between any preferred keyword and any word in the text. |
| `_keyword_variations_score` | `(self, title, description) -> float` | Checks if any variation/synonym of each preferred keyword appears in the text. Returns fraction of matched categories. |
| `_semantic_similarity_score` | `(self, title, description) -> float` | Encodes the job text and preferred jobs text using SentenceTransformer, computes cosine similarity. Uses first 500 chars of description for efficiency. Returns 0 if the model is unavailable. |

---

### 4.7 `naukri_scraper.py` — Naukri.com Job Scraping & Search

**Class: `NaukriScraper`**

A scraper tailored for Naukri.com. Handles login, keyword/location-based job search, and extraction of job details using Naukri-specific CSS selectors with multi-strategy fallbacks.

**Constants:** `BASE_URL = "https://www.naukri.com"`, `LOGIN_URL = "https://www.naukri.com/nlogin/login"`

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self)` | Sets driver, wait, and `logged_in` to initial states. |
| `setup_driver` | `(self)` | Creates a visible (non-headless) Chrome driver via `BrowserSetup.create_interactive_driver()` with 15-second wait. |
| `login` | `(self, email: str, password: str) -> bool` | Navigates to Naukri login page, fills email/password fields, clicks login. Pauses for manual OTP/captcha if the URL doesn't change. Sets `self.logged_in = True` on success. |
| `search_jobs` | `(self, keywords, location, experience, sort_by, max_pages) -> List[Dict]` | Builds Naukri search URLs, iterates through up to `max_pages` result pages, and returns a list of job-card summaries (title, company, url, location, experience, salary, skills_preview). |
| `_build_search_url` | `(self, keywords, location, experience, sort_by, page) -> str` | Constructs a URL like `naukri.com/python-developer-jobs-in-bangalore?experience=3&pageNo=2`. |
| `_parse_search_results` | `(self) -> List[Dict]` | Finds job-card elements on the current page using multiple container selectors and extracts each via `_extract_card_info`. |
| `_extract_card_info` | `(self, card) -> Dict` | Extracts title+URL, company, experience, salary, location, and skill tags from a single job card WebElement. |
| `scrape_job` | `(self, job_url: str) -> Dict` | Loads a Naukri job page and extracts full details. Returns a dict with keys: `url`, `title`, `company`, `location`, `experience`, `salary`, `skills`, `description`, `requirements`, `scraped_at`, `source`. Returns `{}` on failure. |
| `extract_job_title` | `(self) -> str` | Naukri selectors: `h1[class*="jd-header-title"]`, `.jd-header-title`, fallback to first `<h1>`. Returns `"Unknown Title"` if all fail. |
| `extract_company_name` | `(self) -> str` | Naukri selectors: `a[class*="jd-header-comp-name"]`, `a[href*="/company-jobs"]`, etc. Returns `"Unknown Company"` if all fail. |
| `extract_location` | `(self) -> str` | Naukri selectors + fallback scanning header spans for Indian city names. Returns `"Unknown Location"` if all fail. |
| `extract_experience` | `(self) -> str` | Naukri selectors + regex fallback for `X-Y Yrs` pattern. Returns `"Not specified"` if all fail. |
| `extract_salary` | `(self) -> str` | Naukri selectors for salary fields. Returns `"Not disclosed"` if all fail. |
| `extract_skills` | `(self) -> List[str]` | Extracts skill tags/chips from the key-skills section. Returns `[]` if none found. |
| `extract_job_description` | `(self) -> str` | Naukri selectors (`div[class*="job-desc"]`, `div[class*="dang-inner-html"]`) + largest-text-block fallback. Returns `"No description found"` if all fail. |
| `_derive_requirements` | `(self, description, skills) -> List[str]` | Merges extracted skills with tech keywords found in the description. De-duplicates. Includes India-specific qualifications (B.Tech, M.Tech, MCA). |
| `_extract_text` | `(self, selectors) -> Optional[str]` | Helper — tries CSS selectors in order, returns first non-empty text. |
| `_find_first_element` | `(self, selectors)` | Helper — returns first visible element from CSS or XPath selectors. |
| `close` | `(self)` | Quits the browser and resets state. |

---

### 4.8 `naukri_automation.py` — Naukri.com Application Automation

**Class: `NaukriAutomation`**

Automates the Naukri apply workflow. Shares a browser session with `NaukriScraper` (single login). Handles one-click apply, pre-apply chatbot questionnaires, external-apply redirects, and profile resume uploads.

**Constant:** `PROFILE_URL = "https://www.naukri.com/mnjuser/profile"`

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self, naukri_scraper, job_matcher, tracker)` | Stores references to shared `NaukriScraper`, `JobMatcher`, and `ApplicationTracker`. |
| `driver` (property) | | Returns `self.scraper.driver` (shared session). |
| `wait` (property) | | Returns `self.scraper.wait` (shared session). |
| `update_profile_resume` | `(self, resume_path: str) -> bool` | Navigates to Naukri profile, finds file-input or clicks "Update Resume" button first, then sends the file path. Returns `True` on success. |
| `apply_to_job` | `(self, job_url, job_details=None) -> bool` | Full single-job apply pipeline: scrape (if needed) → find Apply button → click → handle chatbot → handle confirmation → verify success → track. Falls back to `_handle_external_apply` if no Apply button is found. |
| `search_and_apply` | `(self, keywords, location, experience, max_applications, max_pages) -> Dict` | End-to-end pipeline: searches Naukri, iterates results, filters with `JobMatcher`, applies to matching jobs, prints a summary. Returns stats dict with `total_found`, `matched`, `applied`, `skipped`, `failed`. |
| `_find_apply_button` | `(self)` | Naukri-specific CSS selectors (`button[class*="apply-button"]`, etc.) + XPath text search. Avoids false positives like "Apply Filters". Returns element or `None`. |
| `_detect_chatbot` | `(self) -> bool` | Checks for visible chatbot/screening/questionnaire dialogs after clicking Apply. |
| `_handle_chatbot_questions` | `(self)` | Auto-fills chatbot fields: text inputs (experience→3, salary→1000000, notice→30, else→Yes), first radio button per group, first dropdown option. Clicks Next/Submit up to 10 rounds. |
| `_find_chatbot_next_button` | `(self)` | Finds Submit/Next/Continue/Save buttons inside chatbot dialogs. |
| `_handle_external_apply` | `(self) -> bool` | Detects "Apply on company site" links and opens them for the user. Returns `True` if found. |
| `_handle_apply_confirmation` | `(self)` | Clicks post-apply confirmation buttons (Submit, Confirm, Done). |
| `_verify_application_success` | `(self) -> bool` | Scans page body for success phrases like "already applied", "application submitted", etc. |
| `_safe_click` | `(self, element) -> bool` | Scrolls to element, clicks it. Falls back to JS click if intercepted by overlay. |

---

### 4.9 `requirements.txt` — Dependencies

```
selenium>=4.15.0          # Browser automation
beautifulsoup4>=4.12.0    # HTML parsing (imported but primarily Selenium is used)
requests>=2.31.0          # HTTP requests (imported in job_scraper but not actively used)
pandas>=2.0.0             # Data manipulation for application tracking
reportlab>=4.0.0          # PDF generation for resumes
webdriver-manager>=4.0.0  # Auto-downloads matching ChromeDriver
openpyxl>=3.1.0           # Excel support for pandas (optional)
```

**Optional (not in requirements.txt):** `sentence-transformers` — enables semantic similarity in `JobMatcher`. The code gracefully falls back if not installed.

---

### 4.10 `setup.sh` — Environment Setup

A bash script that:
1. Creates a Python virtual environment (`venv`).
2. Activates it and installs dependencies from `requirements.txt`.
3. Creates the `resumes/` directory.
4. Prints next-step instructions (install ChromeDriver, customize config, run `main.py`).

---

## 5. Configuration Files

### `config.json` (auto-generated on first run)

```json
{
    "personal_details_file": "personal_details.json",
    "preferred_jobs": ["software engineer", "python developer", "data scientist", "full stack developer", "backend developer"],
    "excluded_companies": [],
    "min_salary": 0,
    "preferred_locations": ["Remote", "New York", "San Francisco"],
    "experience_level": ["Mid-level", "Senior"],
    "naukri": {
        "email": "",
        "password": "",
        "search_keywords": ["python developer", "software engineer"],
        "search_locations": ["Bangalore", "Remote"],
        "experience_years": "3",
        "max_applications_per_session": 20
    }
}
```

> **Note:** `excluded_companies`, `min_salary`, `preferred_locations`, and `experience_level` are defined in the template but **not currently used** in the matching logic. Only `preferred_jobs` is actively consumed by `JobMatcher`.

> **Naukri credentials:** If `email` or `password` are left empty the bot will prompt at runtime. Password input uses `getpass` so it is not echoed to the terminal.

### `personal_details.json` (auto-generated on first run)

Contains: `name`, `email`, `phone`, `location`, `linkedin`, `summary`, `core_skills`, `skills`, `experience` (array of roles with bullets), `education`.

---

## 6. Runtime Artifacts

| File/Directory | Created By | Purpose |
|---|---|---|
| `job_application.log` | `main.py` (logging) | Timestamped log of all operations, warnings, and errors. |
| `job_applications.csv` | `ApplicationTracker` | Persistent record of every application: date, job title, company, location, URL, status, notes. |
| `resumes/resume_YYYYMMDD_HHMMSS.pdf` | `ResumeModifier` | One tailored PDF resume per application. |
| `config.json` | `main.py` (`__main__`) | Created from template if missing. |
| `personal_details.json` | `main.py` (`__main__`) | Created from template if missing. |

---

## 7. Key Design Decisions

- **Centralized browser setup:** `BrowserSetup` in `browser_automation.py` is the single source of truth for all Selenium driver configuration. `JobScraper`, `BrowserAutomation`, `NaukriScraper`, and `NaukriAutomation` all use it.
- **Multi-strategy element finding:** Both scraping and form filling use a cascade of strategies (specific selectors → generic selectors → meta tags → heuristics → iframes) to handle diverse website structures.
- **Shared Naukri session:** `NaukriAutomation` accesses the driver via `NaukriScraper`'s properties so a single login is reused for searching, scraping, and applying.
- **Auto-routing by URL:** `apply_for_job()` in `main.py` automatically detects `naukri.com` URLs and routes them through the Naukri pipeline instead of the generic one.
- **User confirmation before submit:** `BrowserAutomation.submit_application()` always pauses for user confirmation, preventing accidental submissions.
- **Graceful degradation:** Semantic matching (`sentence-transformers`) is optional. The system works with exact, fuzzy, and keyword-variation matching alone.
- **Error popups:** `show_error_popup` in `main.py` pauses execution on errors so the user can intervene, rather than silently failing.

---

## 8. Inter-Module Dependencies

```
main.py
 ├── job_scraper.py
 │    └── browser_automation.py (BrowserSetup)
 ├── resume_modifier.py
 ├── application_tracker.py
 ├── browser_automation.py (BrowserSetup + BrowserAutomation)
 ├── job_matcher.py
 ├── naukri_scraper.py
 │    └── browser_automation.py (BrowserSetup)
 └── naukri_automation.py
      ├── naukri_scraper.py (shared driver session)
      ├── job_matcher.py
      └── application_tracker.py
```

- `job_scraper.py` imports `BrowserSetup` from `browser_automation.py`.
- `naukri_scraper.py` imports `BrowserSetup` from `browser_automation.py`.
- `naukri_automation.py` receives `NaukriScraper`, `JobMatcher`, and `ApplicationTracker` via constructor injection from `main.py`.
- All other modules are independent of each other and only orchestrated through `main.py`.
