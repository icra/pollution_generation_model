def add_data_to_txtinout(pt, compounds, exco_om_df, pollutants_om_df) -> None:
    """
    Updates SWAT input DataFrames with pollutant load data for a specific point.

    This function adds pollutant and nutrient load values from the `compounds` dictionary 
    to the `exco_om_df` and `pollutants_om_df` DataFrames. It modifies these DataFrames in place.

    For known pollutants (e.g., BOD, ammonia, nitrate, etc.), values are added to specific 
    columns in `exco_om_df`. Any other pollutants are assumed to be custom and are updated 
    in `pollutants_om_df`.

    Parameters:
        pt (str): The SWAT identifier (e.g., id_swat) for the point to update.
        compounds (dict[str, float]): A dictionary where keys are pollutant names and values 
            are their daily loads in kg/day.
        exco_om_df (pd.DataFrame): DataFrame representing the contents of the `exco_om.exc` file. 
            Known pollutants will be added to their corresponding columns. Modified in place.
        pollutants_om_df (pd.DataFrame): DataFrame representing the contents of the `pollutants_om.exc` file. 
            Custom pollutants not handled by `exco_om_df` will be updated here. Modified in place.

    Returns:
        None
    """
    contaminants_i_nutrients = compounds.keys()
        
    if 'DBO 5 dies' in compounds:
        dbo = compounds["DBO 5 dies"]
        exco_om_df.loc[exco_om_df['name'] == pt, 'cbod'] += dbo

    if 'Fòsfor orgànic' in compounds:
        fosfor = compounds["Fòsfor orgànic"]
        exco_om_df.loc[exco_om_df['name'] == pt, 'sedp'] += fosfor

    if 'Nitrogen orgànic' in compounds:
        ptl_n = compounds["Nitrogen orgànic"]  #organic nitrogen
        exco_om_df.loc[exco_om_df['name'] == pt, 'orgn'] += ptl_n

    if 'Amoniac' in compounds:
        nh3_n = compounds["Amoniac"]  #ammonia
        exco_om_df.loc[exco_om_df['name'] == pt, 'nh3'] += nh3_n

    if 'Nitrats' in compounds:
        no3_n = compounds["Nitrats"]  #nitrate
        exco_om_df.loc[exco_om_df['name'] == pt, 'no3'] += no3_n

    if 'q' in compounds:
        cabal = compounds["q"]            
        exco_om_df.loc[exco_om_df['name'] == pt, 'flo'] += cabal

    if 'Fosfats' in compounds:
        fosfats = compounds["Fosfats"]
        exco_om_df.loc[exco_om_df['name'] == pt, 'solp'] += fosfats

        
    #Per cadascun dels contaminants que no va a recall_dat, posar-lo a recall_pollutants_dat
    for contaminant in contaminants_i_nutrients:            
        if contaminant not in ["DBO 5 dies", "Fòsfor orgànic", "Nitrogen orgànic", "Amoniac", "Nitrats", "Fosfats"]:
            load = compounds[contaminant]
            pollutants_om_df.loc[(pollutants_om_df['recall_rec'] == pt) & (pollutants_om_df['pollutants_pth'] == contaminant), 'load'] += load
