from pathlib import Path
from .lib.calibrationMainConcentration import read_industries, read_edars
from .lib.db.ConnectPostgree import ConnectDb as pg
import argparse
import json
import sys
import getpass
import os
import importlib.resources
from pathlib import Path

def run_pollutant_generation_model(pollutants: list[str], watershed: str, ignore_industries: bool = True, removal_rate_path: str | Path | None = None, edar_data_xlsx: str | Path | None = None, ):
    pg_url = "217.61.208.188"
    pg_user = "traca_user"
    pg_db = "traca_1"
    
    #check if icra_db_password is set in environment variables
    pg_pass = os.getenv("icra_db_password")
    
    if not pg_pass:
        print("Environment variable 'icra_db_password' not set.")
        pg_pass = getpass.getpass("Please enter the database password for ICRA db: ")

    connection = pg(pg_url, pg_db, pg_user, pg_pass)

    # Access the 'inputs' directory inside the installed package
    with importlib.resources.path("pollution_generation_model.inputs", "") as inputs_path:
        inputs_path = inputs_path.resolve()

        industrial_data = str(inputs_path / 'industrial.xlsx')
        recall_points = str(inputs_path / "recall_points.xlsx")
        table_name = 'cens_v4_1_prova'  # Taula del cens industrial amb estimacions

        if not removal_rate_path:
            removal_rate_path = str(inputs_path / 'atenuacions_generacions.xlsx')

        if not edar_data_xlsx:
            edar_data_xlsx = str(inputs_path / 'edar_data.xlsx')
    
        industries_to_edar, industries_to_river = connection.get_industries_to_edar_and_industry_separated(table_name)
        id_discharge_to_volumes = read_industries(industries_to_river, industrial_data, recall_points, pollutants, connection, removal_rate_path, watershed)      #Dades de contaminants abocats directament a riu o a sortida depuradora
        edars_calibrated = read_edars(pollutants, industries_to_edar, edar_data_xlsx, removal_rate_path, recall_points, watershed, ignore_industries=ignore_industries)    #Dades de contaminants despres de ser filtrats per edar

    result = {
        "wwtp": edars_calibrated,
        "discharge_to_river": id_discharge_to_volumes if not ignore_industries else {},
    }        
    return result


def main():
    
    parser = argparse.ArgumentParser(description="Pollution generation model.")

    parser.add_argument(
        "--watershed",
        choices=["muga", "ter", "fluvia", "llobregat", "sud", "tordera"],
        help="Watershed to get results for (optional). Choose from: muga, ter, fluvia, llobregat, sud, tordera",
        default=None
    )

    parser.add_argument(
        "--removal_rate",
        help="Path to Excel file with removal rates",
        default=None
    )

    parser.add_argument(
        "--pollutants",
        nargs='+',  # '+' means one or more; use '*' if it's optional
        help="List of pollutants to model, separated by spaces (e.g. Venlafaxina Ciprofloxacina)"
    )
    
    parser.add_argument(
        "--wwtp_treatments",
        help="Path to Excel file with WWTP treatments",
        default=None
    )
    
    parser.add_argument(
        "--ignore_industries",
        action="store_true",
        help="Ignore industries and only consider domestic sources (Recommended for most cases)",
        default=True
    )


    args = parser.parse_args()
    
    
    if not args.pollutants:
        print(json.dumps({"error": "No pollutants provided. Use --pollutants argument."}))
        sys.exit(1)
    
    watershed = args.watershed
    removal_rate = args.removal_rate
    pollutants = args.pollutants
    wwtp_treatments = args.wwtp_treatments
    ignore_industries = args.ignore_industries
    
    
    
    try:
        result = run_pollutant_generation_model(pollutants, watershed, ignore_industries, removal_rate, wwtp_treatments)
        print(json.dumps(result))  # stdout
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    

if __name__ == "__main__":
    main()