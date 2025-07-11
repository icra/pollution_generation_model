import sqlite3
from sqlite3 import Error
import pandas as pd
from math import radians, cos, sin, asin, sqrt
import time
import xlsxwriter
from pathlib import Path

class renameSQLite:

    def __init__(self, url):
        self.url = url

    #add pollutant features table to pollutants_pth table
    def add_compound_features(self, conn, compound_features_path):
        df = pd.read_excel(Path(compound_features_path))
        df['description'] = df['name']
        df = df.dropna()

        # reset index and begin at 1
        df = df.reset_index(drop=True)
        df.index += 1

        df = df[['name', 'solub', 'aq_hlife', 'aq_volat', 'mol_wt', 'aq_resus', 'aq_settle', 'ben_act_dep', 'ben_bury', 'ben_hlife', 'kow', 'description']]

        df.to_sql('pollutants_pth', conn, if_exists='replace', index=True, index_label='id')

    #modifications required for converting .sql to txtinout using swat editor
    def modify_file_cio(self, cursor, conn):

        #file cio classification
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_cio_classification'")
        table_exists = cursor.fetchone()

        if table_exists:
            # Check if the id exists in the table
            id_to_check = 31  # Replace with the id you want to check
            cursor.execute("SELECT COUNT(*) FROM file_cio_classification WHERE id=?", (id_to_check,))
            id_count = cursor.fetchone()[0]

            if id_count == 0:
                # The id doesn't exist, so add it
                cursor.execute("INSERT INTO file_cio_classification (id, name) VALUES (?, ?)", (id_to_check, 'pollutants'))
                conn.commit()


        #file cio
        #check if id=148 and id=149 exist in file_cio. if not, create them
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_cio'")
        table_exists = cursor.fetchone()

        if table_exists:
            # Check if the id exists in the table
            id_to_check = 148  # Replace with the id you want to check
            cursor.execute("SELECT COUNT(*) FROM file_cio WHERE id=?", (id_to_check,))
            id_count = cursor.fetchone()[0]

            if id_count == 0:
                # The id doesn't exist, so add it
                cursor.execute("INSERT INTO file_cio (id, classification_id, order_in_class, file_name) VALUES (?, ?, ?, ?)", (id_to_check, 31, 1, 'pollutants.def'))
                conn.commit()

            # Check if the id exists in the table
            id_to_check = 149  # Replace with the id you want to check
            cursor.execute("SELECT COUNT(*) FROM file_cio WHERE id=?", (id_to_check,))
            id_count = cursor.fetchone()[0]

            if id_count == 0:
                # The id doesn't exist, so add it
                cursor.execute(
                    "INSERT INTO file_cio (id, classification_id, order_in_class, file_name) VALUES (?, ?, ?, ?)",
                    (id_to_check, 31, 2, 'pollutants_om.exc'))
                conn.commit()


    def add_data_to_swat(self, edars_calibrated, volumes, contaminants_i_nutrients, compound_features_path, conca):

        try:

            conn = sqlite3.connect(self.url)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            #add compound features table
            self.add_compound_features(conn, compound_features_path)
            self.modify_file_cio(c, conn)

            #check if table pollutant_pth exists. if not, create it
            c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='pollutants_pth' ''')

            if c.fetchone()[0] == 0:
                c.execute('''CREATE TABLE pollutants_pth
                             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                             name text, 
                             solub real, 
                             aq_hlife real, 
                             aq_volat real, 
                             mol_wt real, 
                             aq_resus real, 
                             aq_settle real, 
                             ben_act_dep real, 
                             ben_bury real, 
                             ben_hlife real, 
                             description text)''')
                conn.commit()

            #check if table recall_pollutants_dat exists. if not, create it
            c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='recall_pollutants_dat' ''')

            if c.fetchone()[0] == 0:
                c.execute('''CREATE TABLE recall_pollutants_dat (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                              recall_rec_id INTEGER, 
                              pollutants_pth_id INTEGER, 
                              jday INTEGER, 
                              mo INTEGER, 
                              day_mo INTEGER, 
                              yr INTEGER, 
                              load INTEGER,
                              FOREIGN KEY (recall_rec_id) REFERENCES recall_rec(id),
                              FOREIGN KEY (pollutants_pth_id) REFERENCES pollutants_pth(id))''')

                conn.commit()


            # Insert data of volumes to swat database
            for point in volumes:

                try:
                    dbo = 0
                    fosfor = 0
                    ptl_n = 0
                    nh3_n = 0
                    no3_n = 0
                    cabal = 0
                    fosfats = 0

                    if 'DBO 5 dies' in volumes[point]:
                        dbo = volumes[point]['DBO 5 dies']
                    if 'Fòsfor orgànic' in volumes[point]:
                        fosfor = volumes[point]['Fòsfor orgànic']
                    if 'Nitrogen orgànic' in volumes[point]:
                        ptl_n = volumes[point]["Nitrogen orgànic"]  # organic nitrogen
                    if 'Amoniac' in volumes[point]:
                        nh3_n = volumes[point]["Amoniac"]  # ammonia
                    if 'Nitrats' in volumes[point]:
                        no3_n = volumes[point]["Nitrats"]  # nitrate
                    if 'q' in volumes[point]:
                        cabal = volumes[point]["q"]
                    if 'Fosfats' in volumes[point]:
                        fosfats = volumes[point]["Fosfats"]

                    # Constant
                    c.execute(
                        ''' UPDATE recall_dat
                              SET flo = ? + flo,
                                  orgn = ? + orgn,
                                  sedp = ? + sedp,
                                  no3 = ? + no3,  
                                  nh3 = ? + nh3,   
                                  cbod = ? + cbod,
                                  solp = ? + solp
                              WHERE ob_name = ?''',
                        (cabal, ptl_n, fosfor, no3_n, nh3_n, dbo, fosfats, point,))


                    #Per cadascun dels contaminants que no va a recall_dat, posar-lo a recall_pollutants_dat
                    for contaminant in contaminants_i_nutrients:
                        if contaminant not in ["DBO 5 dies", "Fòsfor orgànic", "Nitrogen orgànic", "Amoniac", "Nitrats", "Fosfats"] and contaminant in volumes[point]:

                            #Mirem que el contaminant estigui creat a db
                            c.execute(
                                ''' SELECT id FROM pollutants_pth WHERE name = ?''',
                                (contaminant, ))

                            rows = c.fetchall()
                            if len(rows) > 0:
                                #(SELECT id FROM recall_rec WHERE name=?)
                                c.execute(
                                    ''' SELECT * FROM recall_pollutants_dat WHERE recall_rec_id = (SELECT id FROM recall_rec WHERE name=?) and pollutants_pth_id = (SELECT id FROM pollutants_pth WHERE name=?)''',
                                    (point, contaminant,))

                                rows = c.fetchall()

                                #En cas que no existeixi entrada, la creem
                                if len(rows) > 0:
                                    c.execute(
                                        ''' UPDATE recall_pollutants_dat
                                              SET load = ? + load
                                              WHERE (recall_rec_id = (SELECT id FROM recall_rec WHERE name=?) and pollutants_pth_id = (SELECT id FROM pollutants_pth WHERE name=?))''',
                                        (volumes[point][contaminant], point, contaminant))
                                else:
                                    c.execute(
                                        ''' INSERT INTO recall_pollutants_dat (recall_rec_id, pollutants_pth_id, jday, mo, day_mo, yr, load) VALUES 
                                                  ((SELECT id FROM recall_rec WHERE name=?), (SELECT id FROM pollutants_pth WHERE name=?), ?, ?, ?, ?, ?)''',
                                        (point, contaminant, 1, 1, 1, 1, volumes[point][contaminant]))


                except Error as error:
                    print(error)

            # Insertar dades de edars_calibrated
            for edar in edars_calibrated.values():
                try:
                    if "id_swat" in edar and "compounds_effluent" in edar:    #Si no te key "id_swat" es que aboca a mar

                        dbo = 0
                        fosfor = 0
                        ptl_n = 0
                        nh3_n = 0
                        no3_n = 0
                        cabal = 0
                        fosfats = 0

                        if 'DBO 5 dies' in edar["compounds_effluent"]:
                            dbo = edar["compounds_effluent"]["DBO 5 dies"]
                        if 'Fòsfor orgànic' in edar["compounds_effluent"]:
                            fosfor = edar["compounds_effluent"]["Fòsfor orgànic"]
                        if 'Nitrogen orgànic' in edar["compounds_effluent"]:
                            ptl_n = edar["compounds_effluent"]["Nitrogen orgànic"]  #organic nitrogen
                        if 'Amoniac' in edar["compounds_effluent"]:
                            nh3_n = edar["compounds_effluent"]["Amoniac"]  #ammonia
                        if 'Nitrats' in edar["compounds_effluent"]:
                            no3_n = edar["compounds_effluent"]["Nitrats"]  #nitrate
                        if 'q' in edar["compounds_effluent"]:
                            cabal = edar["compounds_effluent"]["q"]
                        if 'Fosfats' in edar["compounds_effluent"]:
                            fosfats = edar["compounds_effluent"]["Fosfats"]


                        # Constant
                        c.execute(
                            ''' UPDATE recall_dat
                                       SET flo = ? + flo,
                                           orgn = ? + orgn,
                                           sedp = ? + sedp,
                                           no3 = ? + no3,
                                           nh3 = ? + nh3,
                                           cbod = ? + cbod,
                                           solp = ? + solp
                                       WHERE ob_name = ?''',
                                 (cabal, ptl_n, fosfor, no3_n, nh3_n, dbo, fosfats, edar["id_swat"]))



                        #Per cadascun dels contaminants que no va a recall_dat, posar-lo a recall_pollutants_dat
                        for contaminant in contaminants_i_nutrients:

                            if contaminant not in ["DBO 5 dies", "Fòsfor orgànic", "Nitrogen orgànic", "Amoniac", "Nitrats", "Fosfats"] and contaminant in edar["compounds_effluent"]:

                                #Mirem que el contaminant estigui creat a db
                                c.execute(
                                    ''' SELECT id FROM pollutants_pth WHERE name = ?''',
                                    (contaminant, ))

                                rows = c.fetchall()
                                if len(rows) > 0:

                                    c.execute(
                                        ''' SELECT * FROM recall_pollutants_dat WHERE recall_rec_id = (SELECT id FROM recall_rec WHERE name=?) and pollutants_pth_id = (SELECT id FROM pollutants_pth WHERE name=?)''',
                                        (edar["id_swat"], contaminant,))

                                    rows = c.fetchall()

                                    #En cas que no existeixi entrada, la creem
                                    if len(rows) > 0:
                                        c.execute(
                                            ''' UPDATE recall_pollutants_dat
                                                  SET load = ? + load
                                                  WHERE (recall_rec_id = (SELECT id FROM recall_rec WHERE name=?) and pollutants_pth_id = (SELECT id FROM pollutants_pth WHERE name=?))''',
                                            (edar["compounds_effluent"][contaminant], edar["id_swat"], contaminant))
                                    else:
                                        c.execute(
                                            ''' INSERT INTO recall_pollutants_dat (recall_rec_id, pollutants_pth_id, jday, mo, day_mo, yr, load) VALUES 
                                                      ((SELECT id FROM recall_rec WHERE name=?), (SELECT id FROM pollutants_pth WHERE name=?), ?, ?, ?, ?, ?)''',
                                            (edar["id_swat"], contaminant, 1, 1, 1, 1, edar["compounds_effluent"][contaminant]))

                except Error as error:
                    print(error)

            conn.commit()

        except Error as e:
            print(e)
            raise e
        finally:
            if conn:
                conn.close()



    def dist(self, lat1, long1, lat2, long2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians
        lat1, long1, lat2, long2 = map(radians, [lat1, long1, lat2, long2])
        # haversine formula
        dlon = long2 - long1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        # Radius of earth in kilometers is 6371
        km = 6371 * c
        return km

    def shortest_dist(self, points, point):

        def f(point1, point2):
            return self.dist(point1[0], point1[1], point2[0], point2[1])

        return min(points, key = lambda x: f(x, point))

    def export_graph_csv(self, edars_calibrated, volumes, contaminants_i_nutrients, file_name = 'graph.csv'):

        recall = pd.read_excel("inputs/recall_points.xlsx", index_col=0).to_dict(orient='index')
        coord_index = list(map(lambda row: list(row.values()), pd.read_csv("inputs/abocaments_ci.csv").to_dict(orient='index').values()))
        pixel_to_poll = pd.read_csv("inputs/AGG_WWTP_df_no_treatment.csv", index_col=1)
        pixel_to_poll.drop(pixel_to_poll.columns[pixel_to_poll.columns.str.contains('unnamed', case=False)], axis=1, inplace=True)

        contaminants_aux = []

        """
        for pollutant in contaminants_i_nutrients:
            contaminants_aux.append(pollutant+"_industrial")
            contaminants_aux.append(pollutant + "_domestic")
        pixel_to_poll.loc[:, contaminants_aux] = 0
        """


        pixel_to_poll.loc[:, contaminants_i_nutrients] = 0

        for edar in edars_calibrated:
            id = int(edars_calibrated[edar]["id_swat"])
            point = [recall[id]['lat'], recall[id]['lon']]

            id_pixel = (self.shortest_dist(coord_index, point))[2]

            for pollutant in contaminants_i_nutrients:
                load = 0
                #load_industrial = 0
                #load_domestic = 0
                if pollutant in edars_calibrated[edar]["compounds_effluent"]:
                    load = (edars_calibrated[edar]["compounds_effluent"][pollutant] * 1000000000 / 24) #kg/dia a micro/h
                    #load_domestic = (edars_calibrated[edar]["compounds_effluent"][pollutant]["domestic"] * 1000000000 / 24) #kg/dia a micro/h
                    #load_industrial = (edars_calibrated[edar]["compounds_effluent"][pollutant]["industrial"] * 1000000000 / 24) #kg/dia a micro/h


                pixel_to_poll.at[id_pixel, pollutant] += load
                #pixel_to_poll.loc[id_pixel, pollutant+"_industrial"] += load_industrial
                #pixel_to_poll.loc[id_pixel, pollutant+"_domestic"] += load_domestic


        #Repetir per industries


        for industry in volumes:
            id = int(volumes[industry]["id"])
            point = [recall[id]['lat'], recall[id]['lon']]
            id_pixel = (self.shortest_dist(coord_index, point))[2]

            for pollutant in contaminants_i_nutrients:
                load = 0
                if pollutant in volumes[industry]:
                    load = (volumes[industry][pollutant] * 1000000000 / 24) #kg/dia a micro/h

                pixel_to_poll.at[id_pixel, pollutant] += load
                #pixel_to_poll.loc[id_pixel, pollutant+"_industrial"] += load

            end = time.time()
        #pixel_to_poll.columns = pixel_to_poll.columns.str.replace('_industrial', '')
        #pixel_to_poll.columns = pixel_to_poll.columns.str.replace('_domestic', '')

        pixel_to_poll.to_csv(file_name)
        return pixel_to_poll

    #Posa les dades de les indústries al graf. Executar abans que add_data_edar_to_graph
    def add_data_industry_to_graph(self, recall_points, volumes, contaminants_i_nutrients, abocaments_ci, id_pixel, conca):

        recall = pd.read_excel(recall_points, index_col=0).to_dict(orient='index')

        coord_index = list(map(lambda row: list(row.values()), pd.read_csv(abocaments_ci).to_dict(orient='index').values()))
        pixel_to_poll = pd.read_csv(id_pixel, index_col=1)
        pixel_to_poll.drop(pixel_to_poll.columns[pixel_to_poll.columns.str.contains('unnamed', case=False)], axis=1, inplace=True)

        #pixel_to_poll.loc[:, contaminants_i_nutrients] = 0
        pixel_to_poll = pixel_to_poll.assign(**{column: 0 for column in contaminants_i_nutrients})

        for industry in volumes:
            id = int(volumes[industry]["id"])

            if recall[id]['conca'] != conca:
                continue

            point = [recall[id]['lat'], recall[id]['lon']]
            id_pixel = (self.shortest_dist(coord_index, point))[2]

            for pollutant in contaminants_i_nutrients:
                load = 0
                if pollutant in volumes[industry]:
                    load = (volumes[industry][pollutant] * 1000000000 / 24) #kg/dia a micro/h

                pixel_to_poll.at[id_pixel, pollutant] += load

        return pixel_to_poll

    def add_data_edar_to_graph(self, recall_points, edars_calibrated, contaminants_i_nutrients, pixel_to_poll, abocaments_ci, conca):

        recall = pd.read_excel(recall_points, index_col=0).to_dict(orient='index')
        coord_index = list(map(lambda row: list(row.values()), pd.read_csv(abocaments_ci).to_dict(orient='index').values()))

        for edar in edars_calibrated:
            id = int(edars_calibrated[edar]["id_swat"])

            if recall[id]['conca'] != conca:
                continue

            point = [recall[id]['lat'], recall[id]['lon']]
            id_pixel = (self.shortest_dist(coord_index, point))[2]

            for pollutant in contaminants_i_nutrients:
                load = 0
                if pollutant in edars_calibrated[edar]["compounds_effluent"]:
                    load = (edars_calibrated[edar]["compounds_effluent"][pollutant] * 1000000000 / 24) #kg/dia a micro/h

                pixel_to_poll.at[id_pixel, pollutant] += load

        return pixel_to_poll

    def add_data_to_excel(self, edars_calibrated, volumes, contaminants_i_nutrients, file_name):
        edars = []
        for eu_id in edars_calibrated:
            edar = edars_calibrated[eu_id]
            obj = {}
            obj["EDAR EU_ID"] = eu_id
            obj["Nom"] = edar["nom"]
            obj["Població"] = edar["population_real"]
            obj["Configuració"] = edar["configuration"]
            obj["Cabal"] = edar["compounds_effluent"]["q"]
            for contaminant in contaminants_i_nutrients:
                if contaminant in edar["compounds_effluent"]:
                    obj[contaminant] = edar["compounds_effluent"][contaminant] * 1000
                else:
                    obj[contaminant] = '-'

            edars.append(obj)

        #pd.DataFrame(edars).to_excel(file_name)

        abocaments = []
        for abocament_id in volumes:
            abocament = volumes[abocament_id]
            obj = {}
            obj['SWAT ID'] = abocament_id
            obj["Abocament"] = abocament["abocament"]
            obj["Cabal"] = abocament["q"]
            for contaminant in contaminants_i_nutrients:
                if contaminant in abocament:
                    obj[contaminant] = abocament[contaminant] * 1000
                else:
                    obj[contaminant] = '-'
            abocaments.append(obj)


        with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
            pd.DataFrame(edars).to_excel(writer, sheet_name='EDAR', startrow=1, startcol=0)
            pd.DataFrame(abocaments).to_excel(writer, sheet_name='Indústries', startrow=1, startcol=0)
