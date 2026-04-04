# Financial Dashboard

Interactive dashboard for personal finance tracking. Developed with Streamlit and integrated with Google Sheets.

## Features

* 📊 **Financial metrics**: Income, expenses, savings, averages, deltas, and annual projections
* 📈 **Interactive charts**: Cumulative savings, savings rate with average line, composition %, and trend analysis
* 🎯 **Monthly highlights**: Identifies best and worst months for income, expenses, and savings
* 📅 **Period filters**: Presets (Last 6/12 months, current year) and custom date range
* 🔐 **Authentication**: Password-protected access with cookie-based session persistence
* 🔄 **Real-time sync**: Data always up to date with your Google Sheets spreadsheet

## 📋 Spreadsheet Structure

> ⚠️ **Disclaimer**
> This spreadsheet is customized for my personal use and is currently private. However, the required structure is simple and can be easily adapted to your needs.

The dashboard reads data from a single Google Sheets spreadsheet. Here's what it expects:

1. **One sheet (tab) per month**, named in Portuguese: `Janeiro 2023`, `Fevereiro 2024`, `Março 2025`, etc. Tabs that don't match this pattern are simply ignored.

2. **Two cells per sheet** — one for total expenses and one for total income:
   | Data         | Default Cell | Constant in code |
   |--------------|:------------:|------------------|
   | **Expenses** | `M27`        | `EXPENSES_CELL`  |
   | **Income**   | `B6`         | `INCOME_CELL`    |

   The values should be in BRL format (e.g. `R$ 1.234,56` or just `1234.56`).

3. **Everything else is computed automatically** — the dashboard calculates savings (`income - expenses`), savings rate (`savings / income × 100`), cumulative totals, averages, deltas, and projections from those two values per month.

### Adapting to your spreadsheet

You only need to change **two constants** at the top of `dashboard.py`:

```python
EXPENSES_CELL = 'M27'  # Change to the cell where your total expenses are
INCOME_CELL = 'B6'     # Change to the cell where your total income is
```

As long as every monthly tab has a total expense value and a total income value somewhere, the dashboard will work. The cells just need to be in the same position across all tabs.

> **Example**: If your spreadsheet has expenses in cell `D50` and income in `D10`, just update the constants to `EXPENSES_CELL = 'D50'` and `INCOME_CELL = 'D10'`.

**In short**: all you need is a Google Sheets spreadsheet with one tab per month (e.g. `Janeiro 2023`) and two cells per tab — one for total expenses and one for total income. The dashboard handles everything else.

## ⚙️ Configuration

### Google Sheets credentials

After creating and setting up your financial spreadsheet with the structure described above, you need to connect it to the dashboard via a Google Cloud service account:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Create a service account and download the JSON key as `credentials.json`
3. Enable the **Google Sheets API**: go to [APIs & Services → Library](https://console.cloud.google.com/apis/library/sheets.googleapis.com), select your project, and click **Enable**
4. Share your spreadsheet with the service account: open your Google Sheets spreadsheet, click **Share**, paste the `client_email` from your `credentials.json` (e.g. `your-service-account@your-project.iam.gserviceaccount.com`), and grant **Viewer** access

**`credentials.json`** format:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/...",
  "universe_domain": "googleapis.com"
}
```

### Authentication

The dashboard requires login to access. Users and passwords are configured in `config.yaml`. Passwords **must** be bcrypt-hashed.

**`config.yaml`** — user credentials, authentication settings, and spreadsheet URL:

```yaml
credentials:
  usernames:
    your_username:
      name: Your Name
      password: $2b$12$...  # bcrypt-hashed password (see below)

cookie:
  name: finance_dashboard_cookie
  key: some_random_secret_key  # any random string
  expiry_days: 30

sheet_url: https://docs.google.com/spreadsheets/d/your-spreadsheet-id/edit
```

To generate a bcrypt hash for the `password` field:

```bash
pip install bcrypt
python -c "import bcrypt; print(bcrypt.hashpw(b'your_password', bcrypt.gensalt()).decode())"
```

Replace `your_password` with your chosen password. This will output something like `$2b$12$LJ3m4ys...` — use that value in the `password` field.

## 💻 Local Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd finance-dashboard
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Add your config files** — create `credentials.json` and `config.yaml` as described above

4. **Run the dashboard**

   ```bash
   streamlit run dashboard.py
   ```

5. **Or run with Docker**

   ```bash
   docker build -t finance-dashboard .
   docker run -p 8501:8501 finance-dashboard
   ```

6. Open `http://localhost:8501` in your browser and log in with the credentials from your `config.yaml`

## 🚀 Deploy to Streamlit Community Cloud

1. Push your repository to GitHub (make sure secrets are **not** committed)
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/) and connect your GitHub repo
3. In the app settings, add your secrets under **Advanced settings → Secrets** using TOML format:

   ```toml
   sheet_url = "https://docs.google.com/spreadsheets/d/your-spreadsheet-id/edit"

   [google_sheets_credentials]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@your-project.iam.gserviceaccount.com"
   client_id = "123456789"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
   universe_domain = "googleapis.com"

   [user_credentials.credentials.usernames.your_username]
   name = "Your Name"
   password = "$2b$12$..."

   [user_credentials.cookie]
   name = "finance_dashboard_cookie"
   key = "some_random_secret_key"
   expiry_days = 30
   ```

   > **Tip**: To convert your `credentials.json` to TOML, copy each JSON field as a key-value pair under `[google_sheets_credentials]`. Strings must be quoted and `\n` in the private key must be preserved as-is.

4. Deploy — Streamlit will install dependencies from `requirements.txt` automatically
5. Once deployed, access your dashboard at `https://your-app-name.streamlit.app` and log in with the credentials configured in your secrets

> For more details, see the [Streamlit deploy documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud).

## 🗂️ Project Structure

```
├── dashboard.py             # Main application
├── streamlit_service.py     # Config loader (secrets / local files)
├── .streamlit/config.toml   # Streamlit theme settings
├── config.yaml              # User credentials (local dev, git-ignored)
├── credentials.json         # Google Sheets credentials (local dev, git-ignored)
├── Dockerfile               # Container for local development
├── requirements.txt         # Python dependencies
└── .gitignore               # Prevents secrets from being committed
```

## 🔒 Security

* **Never commit secrets**: `config.yaml` and `credentials.json` are in `.gitignore`
* **Production**: credentials are stored in [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
* Password-based authentication via `streamlit-authenticator` with bcrypt-hashed passwords
