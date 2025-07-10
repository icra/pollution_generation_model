# 🧪 Pollution Generation Model

This Python package estimates pollutant loads in a watershed by combining industrial and domestic wastewater data. It retrieves and processes information from a PostgreSQL database, along with configuration files provided by the user.

---

## 📦 Installation

Install directly from GitHub using:

```bash
pip install git+https://github.com/icra/pollution_generation_model
```

## 🔐 Database Authentication
The script connects to a PostgreSQL database and requires a password. Set it using an environment variable:
```bash
export icra_db_password='your_password_here'
```
If the variable is not set, you will be prompted for the password during execution.

## From Python:
```bash
from pollution_generation_model.main import run_pollutant_generation_model

os.environ["icra_db_password"] = "your_real_password"

result = run_pollutant_generation_model(
    pollutants=["Venlafaxina", "Ciprofloxacina"],
    watershed="llobregat",
    ignore_industries=True,
    removal_rate_path="path/to/atenuacions_generacions.xlsx",
    edar_data_xlsx="path/to/edar_data.xlsx"
)

print(result)
```

## 🧾 From Command-line Arguments
Run the pollution generation model using the following command:
```bash
run_pollution_generation_model
```
### Arguments

| Argument              | Type     | Required | Description                                                                 |
|-----------------------|----------|----------|-----------------------------------------------------------------------------|
| `--watershed`         | string   | ✅ Yes       | Watershed to model. Choices: `muga`, `ter`, `fluvia`, `llobregat`, `sud`, `tordera`. |
| `--pollutants`        | list     | ✅ Yes   | List of pollutants to model. Example: `--pollutants Venlafaxina Ciprofloxacina`. |
| `--removal_rate`      | path     | No       | Path to Excel file containing removal rates.                               |
| `--wwtp_treatments`   | path     | No       | Path to Excel file with WWTP configuration data.                           |
| `--ignore_industries` | flag     | No       | When used, only domestic sources are considered (industries ignored). Default is True.      |```

### Example
```bash
run_pollution_generation_model --watershed ter --pollutants Venlafaxina Ciprofloxacina
```


## 📂 Data Files

The following Excel files can be optionally provided to customize the model (example files are included in the repository):

- `edar_data.xlsx`: WWTP treatment configuration (optional)
- `atenuacions_generacions.xlsx`: Pollutant removal rates (optional)

Example files can be found in the `examples/` directory of the repository.

## 📤 Output Format

The script outputs a JSON object containing two main sections:

```json
{
  "wwtp": {
    "edar_eu_code": {
      "eu_code": "string",
      "dc_code": "string",
      "nom": "string",
      "population_real": number,
      "configuration": ["P", "SN", "UF", "RO", ...],
      "compounds_effluent": {
        "q": number,                  // Effluent flow (m³/day)
        "pollutant_1": number,        // Load in kg/day
        "pollutant_2": number,
        ...
      }
    },
    ...
  },
  "discharge_to_river": {
    ...
  }
}

