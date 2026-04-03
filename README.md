# 💸 Financial Dashboard

Interactive dashboard for personal finance tracking, developed with Streamlit and integrated with Google Sheets.

## 🚀 How to use

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd dashboard
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

## ⚙️ Configuration

### Google Sheets

> ⚠️ **Disclaimer**
> This spreadsheet is customized for my personal use and is currently private. However, the required structure is simple and can be adapted to your needs.
> The dashboard expects sheets named by month (e.g., "January 2023", "February 2024") and specific cells containing the key financial data. Feel free to modify the structure as needed for your own use.

My template needs:
* Sheets must be named in the format: "January 2023", "February 2024", etc.
* Cell **M27**: Total monthly expenses
* Cell **B6**: Total monthly salary/income


### Authentication (optional)

Configure users and passwords in the `config.yaml` file

## 🌟 Features

* 📊 **Financial metrics**: Total expenses, income, savings, and averages
* 📈 **Interactive charts**: Visual analysis of monthly data
* 🎯 **Highlights**: Identifies best and worst periods
* 📅 **Period filters**: Analyze specific time ranges
* 🔄 **Real-time updates**: Data always synced with the spreadsheet

## 📦 Project Structure

```
├── dashboard.py             # Main application
├── streamlit_service.py     # Helper services
├── config.yaml              # Settings and credentials
├── credentials.json         # Google Sheets credentials
└── requirements.txt         # Python dependencies
```

## 🔒 Security

* Credentials stored securely in configuration files
* Optional password-based authentication
