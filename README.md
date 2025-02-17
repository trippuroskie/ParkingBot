# Parking Bot

An educational parking reservation automation tool with both CLI and web interfaces.

## Prerequisites

1. Honk mobile account with:
   - Saved credit card at [Honk Payment Cards](https://parking.honkmobile.com/payment-cards)
   - Single license plate at [Honk Vehicles](https://parking.honkmobile.com/vehicles)
2. Python 3.7+
3. Chrome browser

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up `.env` file:
   ```bash
   HONK_USERNAME=your_email
   HONK_PASSWORD=your_password
   ```

## Usage

### Web Interface
```bash
streamlit run main_st.py
```

### Command Line
```bash
python main.py
```


## Disclaimer

For educational purposes only. Use responsibly and in accordance with Brighton Resort's terms of service.
