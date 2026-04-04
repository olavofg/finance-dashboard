# 💸 Financial Dashboard

Interactive dashboard for personal finance tracking, developed with Streamlit and integrated with Google Sheets.

## 🚀 How to use

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd finance-dashboard
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Google Sheets credentials**

   * Create a `credentials.json` file with your Google Sheets API credentials
   * Set the spreadsheet URL in the `config.yaml` file

4. **Run the dashboard**

   ```bash
   streamlit run dashboard.py
   ```

5. **Or run with Docker**

   ```bash
   docker build -t finance-dashboard .
   docker run -p 8501:8501 finance-dashboard
   ```

## ⚙️ Configuration

### Google Sheets

> ⚠️ **Disclaimer**
> This spreadsheet is customized for my personal use and is currently private. However, the required structure is simple and can be easily adapted to your needs.

#### How the code reads your spreadsheet

The dashboard reads data from a single Google Sheets spreadsheet. Here's what it expects:

1. **One sheet (tab) per month**, named in Portuguese: `Janeiro 2023`, `Fevereiro 2024`, `Março 2025`, etc. Tabs that don't match this pattern are simply ignored.

2. **Two cells per sheet** — one for total expenses and one for total income:
   | Data         | Default Cell | Constant in code |
   |--------------|:------------:|------------------|
   | **Expenses** | `M27`        | `EXPENSES_CELL`  |
   | **Income**   | `B6`         | `INCOME_CELL`    |

   The values should be in BRL format (e.g. `R$ 1.234,56` or just `1234.56`).

3. **Everything else is computed automatically** — the dashboard calculates savings (`income - expenses`), savings rate (`savings / income × 100`), cumulative totals, averages, deltas, and projections from those two values per month.

#### Adapting to your spreadsheet

You only need to change **two constants** at the top of `dashboard.py`:

```python
EXPENSES_CELL = 'M27'  # Change to the cell where your total expenses are
INCOME_CELL = 'B6'     # Change to the cell where your total income is
```

As long as every monthly tab has a total expense value and a total income value somewhere, the dashboard will work. The cells just need to be in the same position across all tabs.

> **Example**: If your spreadsheet has expenses in cell `D50` and income in `D10`, just update the constants to `EXPENSES_CELL = 'D50'` and `INCOME_CELL = 'D10'`.


### Authentication (optional)

Configure users and passwords in the `config.yaml` file

### Local config files

**`config.yaml`** — user credentials, authentication settings, and spreadsheet URL:

```yaml
credentials:
  usernames:
    your_username:
      name: Your Name
      password: $2b$12$...  # bcrypt-hashed password

cookie:
  name: finance_dashboard_cookie
  key: some_random_secret_key
  expiry_days: 30

sheet_url: https://docs.google.com/spreadsheets/d/your-spreadsheet-id/edit
```

**`credentials.json`** — Google Sheets service account credentials:

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
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

> Download this file from the Google Cloud Console under **IAM & Admin → Service Accounts → Keys**.

## 🌟 Features

* 📊 **Financial metrics**: Total expenses, income, savings, and averages
* 📈 **Interactive charts**: Visual analysis of monthly data
* 🎯 **Highlights**: Identifies best and worst periods
* 📅 **Period filters**: Analyze specific time ranges
* 🔄 **Real-time updates**: Data always synced with the spreadsheet

## 📦 Project Structure

```
├── dashboard.py             # Main application
├── streamlit_service.py     # Config loader (secrets / local files)
├── config.yaml              # User credentials (local dev, git-ignored)
├── credentials.json         # Google Sheets credentials (local dev, git-ignored)
├── Dockerfile               # Local development container
├── requirements.txt         # Python dependencies
└── .gitignore               # Prevents secrets from being committed
```

## 🔒 Security

* **Never commit secrets**: `config.yaml` and `credentials.json` are in `.gitignore`
* **Production**: credentials are stored in [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
* Optional password-based authentication via `streamlit-authenticator`
