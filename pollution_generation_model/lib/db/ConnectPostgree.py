import psycopg2
from numpy import *
from itertools import groupby
import statistics
import openpyxl
import pandas as pd
from sqlalchemy import create_engine
import os
import getpass

def create_icra_engine():
    #check if icra_db_password is set in environment variables
    pg_pass = os.getenv("icra_db_password")
    
    if not pg_pass:
        print("Environment variable 'icra_db_password' not set.")
        pg_pass = getpass.getpass("Please enter the database password for ICRA db: ")

    return create_engine(f'postgresql://traca_user:{pg_pass}@217.61.208.188:5432/traca_1')

class ConnectDb:
    """A simple to connect to postgree db"""

    def __init__(self, host, database, user, password):
        self.conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password)

        self.engine = create_icra_engine()

        try:
            # create a cursor
            cur = self.conn.cursor()

            # execute a statement
            #print('PostgreSQL database version:')
            cur.execute('SELECT version()')

            # display the PostgreSQL database server version
            db_version = cur.fetchone()
            #print(db_version)

            # close the communication with the PostgreSQL
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def testConnection(self, host, database, user, password):

        try:
            conn = psycopg2.connect(
                host=host,
                database=database,
                user=user,
                password=password)
            # create a cursor
            cur = conn.cursor()

            # execute a statement
            print('PostgreSQL database version:')
            cur.execute('SELECT version()')

            # display the PostgreSQL database server version
            db_version = cur.fetchone()
            cur.close()

            return True, db_version
            # close the communication with the PostgreSQL

        except (Exception, psycopg2.DatabaseError) as error:
            return False, error

    def getAllWWTP(self):
        try:
            cur = self.conn.cursor()
            cur.execute('SELECT * FROM uwwtps_cod_aca')

            return cur.fetchall()

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def getIndustriesToEdar(self):
        try:
            cur = self.conn.cursor()
            cur.execute('SELECT * FROM industry_to_edar_2')
            return cur.fetchall()

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def getIndustriesToRiver(self, list_of_industries):
        try:
            cur = self.conn.cursor()
            query = 'SELECT tid, "activitat/ubicacio", nom_abocament, cod_ccae, ccae, "Tipus (LLM)", "Subtipus (LLM)", nom_variable, valor_maxim, unitats FROM cens_v3_full WHERE "activitat/ubicacio" || \' \' || "nom_abocament" IN ('
            for i in list_of_industries:
                query += " '" + i.replace('\'', '\'\'') + "',"
            query = query[:-1]
            query += ')'
            cur.execute(query)
            return cur.fetchall()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def get_contaminants_i_nutrients_tipics(self):
        cur = self.conn.cursor()
        cur.execute('SELECT component FROM tipus_components_atenuacio_depuradora')
        components = list(map(lambda component: component[0], cur.fetchall()))  # [comp_1, ..., comp_n]
        return components

    def get_contaminants_i_nutrients_puntuals(self):
        cur = self.conn.cursor()
        cur.execute('SELECT component FROM tipus_components_calibrar')
        components = list(map(lambda component: component[0], cur.fetchall()))  # [comp_1, ..., comp_n]
        return components

    def get_contaminants_i_nutrients_calibrats_wwtp(self):
        cur = self.conn.cursor()
        cur.execute('SELECT component FROM tipus_components_calibrats_depuradora')
        components = list(map(lambda component: component[0], cur.fetchall()))  # [comp_1, ..., comp_n]
        return components

    def getIndustries(self, table='cens_v4_1_prova'):
        try:
            cur = self.conn.cursor()
            query = 'SELECT * FROM ' + table
            cur.execute(query)
            return cur.fetchall()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def ccae_remove_category(self, code, level):
        if len(code) < 5:
            return code
        else:
            return code[:-level]

    def generate_industrial_data(self):
        cur = self.conn.cursor()

        #Compounds
        components = self.get_contaminants_i_nutrients_tipics()

        #Cens industrial
        cur.execute('SELECT nom_variable, unitats, valor_minim, valor_maxim, ccae_l, isic_l FROM cens_v4')
        cens = list(cur.fetchall())
        cens_filtrat = list(filter(lambda x: x[0] in components and x[1] is not None, cens))

        """
        #Tots els compostos estan en les mateixes unitats (µg/l, ng/l, mg/l)
        cens_filtrat.sort(key = lambda x: (x[0], x[1]))
        for key, group in groupby(cens_filtrat, lambda x: (x[0], x[1])):
            compostos_grouped = list(group)
            print(compostos_grouped)
        """

        contaminants_per_tipologia = {}
        contaminants_per_tipologia_mitjanes = {}
        isic_to_ccae = {}

        step_0 = 0
        step_1 = 0
        step_2 = 0
        step_3 = 0


        # Agrupar per contaminant i codi de cens
        cens_filtrat.sort(key=lambda x: (x[0], x[4]))

        for key, group in groupby(cens_filtrat, lambda x: (x[0], x[4])):
            compostos_grouped = list(group)
            for compost in compostos_grouped:
                (contaminant, unitats, valor_minim, valor_maxim, ccae_l, isic_l) = compost
                if isic_l not in isic_to_ccae:
                    isic_to_ccae[isic_l] = ccae_l   #Guardem traduccio de isic a ccae
                if valor_minim is not None and valor_maxim is not None:
                    valor_mitja = (float(valor_minim) + float(valor_maxim)) / 2
                elif valor_minim is not None:
                    valor_mitja = float(valor_minim)
                else:
                    valor_mitja = float(valor_maxim)
                #Passem tot a mg/l
                if "µg/l" in unitats:
                    valor_mitja = valor_mitja / 1000
                elif "ng/l" in unitats:
                    valor_mitja = valor_mitja / 1000000

                new_ccae_l = self.ccae_remove_category(ccae_l, 1)

                if new_ccae_l not in contaminants_per_tipologia:
                    contaminants_per_tipologia[new_ccae_l] = {}
                    contaminants_per_tipologia_mitjanes[new_ccae_l] = {}
                if contaminant not in contaminants_per_tipologia[new_ccae_l]:
                    contaminants_per_tipologia[new_ccae_l][contaminant] = []
                    #contaminants_per_tipologia_mitjanes[new_ccae_l][contaminant] = None

                contaminants_per_tipologia[new_ccae_l][contaminant].append(valor_mitja)
                step_0 += 1


        """
        for ccae_l in contaminants_per_tipologia:
            for compound in contaminants_per_tipologia[ccae_l]:
                valors = contaminants_per_tipologia[ccae_l][compound]
                if len(valors) >= 4:
                    mitjana = statistics.mean(valors)
                    sd = statistics.stdev(valors)
                    cv = sd / mitjana
                    if (cv <= 1.5):
                        contaminants_per_tipologia_mitjanes[ccae_l][compound] = mitjana
                        step_1 += 1
        """
        #Info Nils
        wb_ptr = openpyxl.load_workbook("inputs/means&stds.xlsx")
        ws_ptr = wb_ptr["Sheet 1"]
        isFirst = True

        for row in ws_ptr.iter_rows():
            if isFirst:
                isFirst = False
                continue
            isic = row[0].value
            compound = row[1].value
            if row[2].value is None: break
            mean = float(row[2].value)
            sd = float(row[3].value)
            if isic in isic_to_ccae:
                cod_ccae = self.ccae_remove_category(isic_to_ccae[isic], 1)
                if compound in components:
                    if cod_ccae not in contaminants_per_tipologia_mitjanes:
                        contaminants_per_tipologia_mitjanes[cod_ccae] = {}
                    if compound not in contaminants_per_tipologia_mitjanes[cod_ccae]:
                        contaminants_per_tipologia_mitjanes[cod_ccae][compound] = None

                    #Si coincideixen categories CCAE, fem mitjana
                    if contaminants_per_tipologia_mitjanes[cod_ccae][compound] is None:
                        contaminants_per_tipologia_mitjanes[cod_ccae][compound] = [mean/1000000]  #ng/L a mg/L
                        step_2 += 1
                    elif type(contaminants_per_tipologia_mitjanes[cod_ccae][compound]) == list:
                        contaminants_per_tipologia_mitjanes[cod_ccae][compound].append(mean/1000000)  #ng/L a mg/L
                        step_2 += 1

        for ccae in contaminants_per_tipologia_mitjanes:
            for compound in contaminants_per_tipologia_mitjanes[ccae]:
                if type(contaminants_per_tipologia_mitjanes[ccae][compound]) == list:
                    contaminants_per_tipologia_mitjanes[ccae][compound] = sum(contaminants_per_tipologia_mitjanes[ccae][compound]) / len(contaminants_per_tipologia_mitjanes[ccae][compound])

        #DB francesa

        cur.execute('SELECT valor, variable, cod_ccae FROM bd_francesa')
        db = list(cur.fetchall())
        db_filtrat = list(filter(lambda x: x[1] in components, db))
        for (valor, compound, cod_ccae) in db_filtrat:
            cod_ccae = self.ccae_remove_category(cod_ccae, 1)
            if cod_ccae not in contaminants_per_tipologia_mitjanes:
                contaminants_per_tipologia_mitjanes[cod_ccae] = {}
            if compound not in contaminants_per_tipologia_mitjanes[cod_ccae]:
                contaminants_per_tipologia_mitjanes[cod_ccae][compound] = None

            # Si coincideixen categories CCAE, fem mitjana
            if contaminants_per_tipologia_mitjanes[cod_ccae][compound] is None:
                contaminants_per_tipologia_mitjanes[cod_ccae][compound] = [valor / 1000]  #Passem de µg/l a mg/l
                step_3 += 1
            elif type(contaminants_per_tipologia_mitjanes[cod_ccae][compound]) == list:
                contaminants_per_tipologia_mitjanes[cod_ccae][compound].append(valor / 1000)  #Passem de µg/l a mg/l
                step_3 += 1

        for ccae in contaminants_per_tipologia_mitjanes:
            for compound in contaminants_per_tipologia_mitjanes[ccae]:
                if type(contaminants_per_tipologia_mitjanes[ccae][compound]) == list:
                    contaminants_per_tipologia_mitjanes[ccae][compound] = sum(contaminants_per_tipologia_mitjanes[ccae][compound]) / len(contaminants_per_tipologia_mitjanes[ccae][compound])

        return contaminants_per_tipologia_mitjanes

    def add_industry_to_edar(self, industries_to_edar, industry):
        tid, activitat_ubicacio, tipus_activitat, cod_ccae, tipus_llm, subtipus_llm, nom_abocament, nom_variable, valor_minim, valor_maxim, unitats, ccae_l, nace_l, isic_l, blocs, tipus, cod_ccae_xs, origen, uwwCode = industry

        if uwwCode not in industries_to_edar:
            industries_to_edar[uwwCode] = {}
        if activitat_ubicacio + ' ' + nom_abocament not in industries_to_edar[uwwCode]:
            industries_to_edar[uwwCode][activitat_ubicacio + ' ' + nom_abocament] = []
        industries_to_edar[uwwCode][activitat_ubicacio + ' ' + nom_abocament].append({
            "tid": tid,
            "activitat/ubicacio": activitat_ubicacio,
            "nom_abocament": nom_abocament,
            "cod_ccae": cod_ccae,
            "Tipus (LLM)": tipus_llm,
            "Subtipus (LLM)": subtipus_llm,
            "nom_variable": nom_variable,
            "valor_minim": valor_minim,
            "valor_maxim": valor_maxim,
            "unitats": unitats,
            "uwwCode": uwwCode,
        })

    def add_industry_to_river(self, industries_to_river, industry):
        tid, activitat_ubicacio, tipus_activitat, cod_ccae, tipus_llm, subtipus_llm, nom_abocament, nom_variable, valor_minim, valor_maxim, unitats, ccae_l, nace_l, isic_l, blocs, tipus, cod_ccae_xs, origen, uwwCode = industry

        if activitat_ubicacio + ' ' + nom_abocament not in industries_to_river:
            industries_to_river[activitat_ubicacio + ' ' + nom_abocament] = []
        industries_to_river[activitat_ubicacio + ' ' + nom_abocament].append({
            "tid": tid,
            "activitat/ubicacio": activitat_ubicacio,
            "nom_abocament": nom_abocament,
            "cod_ccae": cod_ccae,
            "Tipus (LLM)": tipus_llm,
            "Subtipus (LLM)": subtipus_llm,
            "nom_variable": nom_variable,
            "valor_minim": valor_minim,
            "valor_maxim": valor_maxim,
            "unitats": unitats,
        })

    def get_industries_to_edar_and_industry_separated(self, table='cens_v4_1_prova'):

        industries = self.getIndustries(table)
        industries_to_edar = {}
        industries_to_river = {}

        for industry in industries:

            tid, activitat_ubicacio, tipus_activitat, cod_ccae, tipus_llm, subtipus_llm, nom_abocament, nom_variable, valor_minim, valor_maxim, unitats, ccae_l, nace_l, isic_l, blocs, tipus, cod_ccae_xs, origen, uwwCode = industry

            if uwwCode is not None:     #industria aboca a depuradora
                if subtipus_llm != "Directe a Terreny" and subtipus_llm != "Indirecte a Terreny" and subtipus_llm != "Directe a Mar" and subtipus_llm != "Indirecte a Mar" and subtipus_llm != "Directe a Riu" and subtipus_llm != "Indirecte a Riu":
                    if tipus_llm in ["Abocament", "Depuradora", "Entrada EDAR"]:  # Influent depuradora
                        self.add_industry_to_edar(industries_to_edar, industry)
                    else:   #No passa per depuradora
                        self.add_industry_to_river(industries_to_river, industry)
                else:    #No passa per depuradora
                    self.add_industry_to_river(industries_to_river, industry)
            else:  # No passa per depuradora
                self.add_industry_to_river(industries_to_river, industry)

            """
            if uwwCode is not None:  # industria aboca a depuradora
                # if tipus_llm in ["Abocament", "Depuradora", "Entrada EDAR"]:    #Influent depuradora
                if tipus_llm in ["Abocament", "Depuradora", "Entrada EDAR"]:
                    self.add_industry_to_edar(industries_to_edar, industry)
                else:  # No passa per depuradora
                    self.add_industry_to_river(industries_to_river, industry)
            else:  # No passa per depuradora
                self.add_industry_to_river(industries_to_river, industry)
            """

        return industries_to_edar, industries_to_river

    def get_edar_scarce(self):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM edar_scarce_2')

        rows = cur.fetchall()

        dict = {
            'ES9080010001010E': {}, #Abrera
            'ES9083020001010E': {}, #Igualada
            'ES9081130006010E': {}, #Manresa
        }

        for row in rows:
            wwtp = row[13]
            contaminant = row[3]
            valor = row[4]

            if wwtp == 'DEPABR-I':
                if contaminant not in dict['ES9080010001010E']:
                    dict['ES9080010001010E'][contaminant] = {'influent': [], 'efluent': []}
                dict['ES9080010001010E'][contaminant]['influent'].append(valor / 1000)
            elif wwtp == 'DEPABR-O':
                if contaminant not in dict['ES9080010001010E']:
                    dict['ES9080010001010E'][contaminant] = {'influent': [], 'efluent': []}
                dict['ES9080010001010E'][contaminant]['efluent'].append(valor / 1000)

            if wwtp == 'DEPIGU-I':
                if contaminant not in dict['ES9083020001010E']:
                    dict['ES9083020001010E'][contaminant] = {'influent': [], 'efluent': []}
                dict['ES9083020001010E'][contaminant]['influent'].append(valor / 1000)
            elif wwtp == 'DEPIGU-O':
                if contaminant not in dict['ES9083020001010E']:
                    dict['ES9083020001010E'][contaminant] = {'influent': [], 'efluent': []}
                dict['ES9083020001010E'][contaminant]['efluent'].append(valor / 1000)


            if wwtp == 'DEPMAN-I':
                if contaminant not in dict['ES9081130006010E']:
                    dict['ES9081130006010E'][contaminant] = {'influent': [], 'efluent': []}
                dict['ES9081130006010E'][contaminant]['influent'].append(valor / 1000)
            elif wwtp == 'DEPMAN-O':
                if contaminant not in dict['ES9081130006010E']:
                    dict['ES9081130006010E'][contaminant] = {'influent': [], 'efluent': []}
                dict['ES9081130006010E'][contaminant]['efluent'].append(valor / 1000)


        return dict

    def get_effluent_observations_edars(self):
        command = 'SELECT * FROM edars_effluent'
        return pd.read_sql(command, con=self.engine).to_dict('records')

    def getIndustryPollution(self, nom_industria, nom_abocament, contaminant, table='cens_v4_1_prova'):
        try:
            cur = self.conn.cursor()
            query = """SELECT * FROM """ + table + """ WHERE "activitat/ubicacio" = '""" + nom_industria + """' and nom_abocament = '""" + nom_abocament + """'"""
            cur.execute(query)
            abocaments_industria = cur.fetchall()
            try:
                abocaments_contaminant = max(map(lambda entry: float(entry[9]),
                                                 filter(lambda entry: entry[7] == contaminant, abocaments_industria)))
            except:
                abocaments_contaminant = 0
            try:
                cabal = max(map(lambda entry: float(entry[9]), filter(lambda entry: entry[7] == "Cabal diari", abocaments_industria)))
            except:
                cabal = 0

            return abocaments_contaminant*cabal
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    #funcions auxiliars
    def read_all_data(self, table='cens_v4_1_prova'):
        industries = self.getIndustries(table)
        industries_to_river = {}
        industries_grouped = {}

        for industry in industries:
            tid, activitat_ubicacio, tipus_activitat, cod_ccae, tipus_llm, subtipus_llm, nom_abocament, nom_variable, valor_minim, valor_maxim, unitats, ccae_l, nace_l, isic_l, blocs, tipus, cod_ccae_xs, origen, uwwCode = industry
            if activitat_ubicacio + ' ' + nom_abocament not in industries_to_river:
                industries_to_river[activitat_ubicacio + ' ' + nom_abocament] = []
            industries_to_river[activitat_ubicacio + ' ' + nom_abocament].append({
                "tid": tid,
                "activitat/ubicacio": activitat_ubicacio,
                "tipus_activitat": tipus_activitat,
                "cod_ccae": cod_ccae,
                "Tipus (LLM)": tipus_llm,
                "Subtipus (LLM)": subtipus_llm,
                "nom_abocament": nom_abocament,
                "nom_variable": nom_variable,
                "valor_minim": valor_minim,
                "valor_maxim": valor_maxim,
                "unitats": unitats,
                "ccae_l": ccae_l,
                "nace_l": nace_l,
                "isic_l": isic_l,
                "blocs": blocs,
                "tipus": tipus,
                "cod_ccae_xs": cod_ccae_xs,
                "origen": origen,
                "uwwCode": uwwCode
            })

        for key, industry in industries_to_river.items():
            aux_point = {
                "activitat/ubicacio": industry[0]["activitat/ubicacio"],
                "tipus_activitat": industry[0]["tipus_activitat"],
                "cod_ccae": industry[0]["cod_ccae"],
                "Tipus (LLM)": industry[0]["Tipus (LLM)"],
                "Subtipus (LLM)": industry[0]["Subtipus (LLM)"],
                "nom_abocament": industry[0]["nom_abocament"],
                "ccae_l": industry[0]["ccae_l"],
                "nace_l": industry[0]["nace_l"],
                "isic_l": industry[0]["isic_l"],
                "blocs": industry[0]["blocs"],
                "tipus": industry[0]["tipus"],
                "cod_ccae_xs": industry[0]["cod_ccae_xs"],
                "uwwCode": industry[0]["uwwCode"]
            }

            for compound in industry:
                if compound["valor_minim"] is not None or compound["valor_maxim"] is not None:
                    if compound["valor_minim"] is not None and compound["valor_maxim"] is not None:
                        valor_mitja = (float(compound["valor_minim"]) + float(compound["valor_maxim"])) / 2
                    elif compound["valor_maxim"] is not None:
                        valor_mitja = float(compound["valor_maxim"])
                    elif compound["valor_minim"] is not None:
                        valor_mitja = float(compound["valor_minim"])

                    """
                    Passem tot a mg/l (tots els contaminents que tractem estan en µg/l, ng/l o mg/l, el cabal 
                    esta en m3/dia o m3/any i no es veu afectat)
                    """
                    unitats = compound["unitats"]
                    if unitats is not None:
                        if "µg/l" in unitats:
                            valor_mitja = valor_mitja / 1000
                        elif "ng/l" in unitats:
                            valor_mitja = valor_mitja / 1000000

                    aux_point[compound["nom_variable"]] = valor_mitja

            industries_grouped[key] = aux_point

        return industries_grouped

    def upload_data(self, industries_grouped, contaminants_i_nutrients, estimacions, table_name = 'cens_v4_1_prova'):

        tid = 0
        compounds = contaminants_i_nutrients.copy()
        compounds.append("Cabal diari")
        compounds.append("Cabal anual")
        compounds.append("Cabal")
        c = self.conn.cursor()


        try:
            query = """drop table """ + table_name
            c.execute(query)
        except BaseException as e:
            print(e)
            pass
        self.conn.commit()
        #query = """select * into """ + table_name + """ from cens_v4 where 0"""
        query = 'CREATE TABLE '+ table_name +' (LIKE cens_v4 INCLUDING ALL)'
        c.execute(query)
        self.conn.commit()

        for industry in industries_grouped.values():
            activitat_ubicacio = industry["activitat/ubicacio"]
            tipus_activitat = industry["tipus_activitat"]
            cod_ccae = industry["cod_ccae"]
            tipus_llm = industry["Tipus (LLM)"]
            subtipus_llm = industry["Subtipus (LLM)"]
            nom_abocament = industry["nom_abocament"]
            ccae_l = industry["ccae_l"]
            nace_l = industry["nace_l"]
            isic_l = industry["isic_l"]
            blocs = industry["blocs"]
            tipus = industry["tipus"]
            cod_ccae_xs = industry["cod_ccae_xs"]
            uwwCode = industry["uwwCode"]

            for contaminant in compounds:
                estimation = None
                new_ccae = self.ccae_remove_category(ccae_l, 1)
                if new_ccae in estimacions:
                    if contaminant in estimacions[new_ccae]:
                        estimation = estimacions[new_ccae][contaminant]

                if contaminant in industry or estimation is not None:

                    nom_variable = contaminant

                    if nom_variable == 'Cabal diari':
                        unitats = "m3/dia"
                    elif nom_variable == 'Cabal anual':
                        unitats = "m3/any"
                    elif nom_variable == "Cabal" and unitats == 'm3/h' and "Cabal diari" not in industry and "Cabal anual" not in industry:
                        nom_variable = "Cabal diari"
                        unitats = "m3/dia"
                        industry[contaminant] *= 24
                    else:
                        unitats = "mg/l"

                    """
                    if contaminant in industry:
                        valor_maxim = industry[contaminant]
                        origen = "ACA"
                    elif estimation is not None:
                        valor_maxim = estimation
                        origen = "ICRA"
                    """

                    #Encara que tenim cabal com a contaminant, com que estimation sera None, no agafara cap estimacio
                    if estimation is not None and contaminant in industry:
                        valor_maxim = max(estimation, industry[contaminant])
                        origen = "ICRA"
                    elif estimation is not None:
                        valor_maxim = estimation
                        origen = "ICRA"
                    elif contaminant in industry:
                        valor_maxim = industry[contaminant]
                        origen = "ACA"


                    if valor_maxim > 0:
                        tid += 1

                    query = """INSERT INTO """+table_name+""" (tid, "activitat/ubicacio", "Tipus Activitat/Ubicació (A/U)", cod_ccae, "Tipus (LLM)", "Subtipus (LLM)", nom_abocament, nom_variable, valor_minim, valor_maxim, unitats, ccae_l, nace_l, isic_l, blocs, tipus, cod_ccae_xs, origen, "uwwCode") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                    params = (tid, activitat_ubicacio, tipus_activitat, cod_ccae, tipus_llm, subtipus_llm, nom_abocament, nom_variable, None, valor_maxim, unitats, ccae_l, nace_l, isic_l, blocs, tipus, cod_ccae_xs, origen, uwwCode)

                    c.execute(query, params)
                    print(tid)

        self.conn.commit()

    def matrix_size(self):
        pollutant_per_ccae = {}
        industries = self.read_all_data()
        contaminants = self.get_contaminants_i_nutrients_tipics()
        for industry in industries:
            for contaminant in contaminants:
                if contaminant in industries[industry] and industries[industry][contaminant] > 0:
                    new_ccae = self.ccae_remove_category(industries[industry]["cod_ccae"], 1)
                    if new_ccae not in pollutant_per_ccae:
                        pollutant_per_ccae[new_ccae] = set()
                    pollutant_per_ccae[new_ccae].add(contaminant)
        return pollutant_per_ccae


        n_cell = 0
        for industry in industries:
            new_ccae = self.ccae_remove_category(industries[industry]["cod_ccae"], 1)
            if new_ccae in pollutant_per_ccae:
                n_cell += len(pollutant_per_ccae[new_ccae])

        print('---------', n_cell)

    def avg_estacions_riu(self, contaminant):

        def f(unit, value):
            if "µg" in unit:
                return float(value) / 1000
            elif "ng" in unit:
                return float(value) / 1000000
            else:
                return float(value)

        try:
            concentracions_estacions_pd = pd.read_sql(
                "SELECT valor, unidad_med FROM estacions_full where variable = '" + contaminant + "'", self.engine)

            concentracions_estacions_list = list(
                concentracions_estacions_pd.apply(lambda row: f(row['unidad_med'], row['valor']), axis=1))

            avg_concentracions_estacions = sum(concentracions_estacions_list) / len(concentracions_estacions_list)

            return avg_concentracions_estacions

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def estadistiques_final(self):

        ind_origen = set()
        ind_code = set()
        industries_location = pd.read_csv('inputs/industries_location.csv', index_col=0).to_dict(orient = 'index')


        industries = self.getIndustries()
        industries_to_edar = {}
        industries_to_river = {}

        n_1 = set()
        n_2 = set()
        n_3 = set()

        for industry in industries:
            tid, activitat_ubicacio, tipus_activitat, cod_ccae, tipus_llm, subtipus_llm, nom_abocament, nom_variable, valor_minim, valor_maxim, unitats, ccae_l, nace_l, isic_l, blocs, tipus, cod_ccae_xs, origen, uwwCode = industry

            ind_code.add((industries_location[activitat_ubicacio + ' ' + nom_abocament]['x'],
                               industries_location[activitat_ubicacio + ' ' + nom_abocament]['y'], self.ccae_remove_category(ccae_l, 1)))

            if uwwCode is not None:     #industria aboca a depuradora
                if tipus_llm in ["Abocament", "Depuradora", "Entrada EDAR"]:    #Influent depuradora
                    self.add_industry_to_edar(industries_to_edar, industry)
                    ind_origen.add((industries_location[activitat_ubicacio+' '+nom_abocament]['x'], industries_location[activitat_ubicacio+' '+nom_abocament]['y'], 1))
                    n_1.add((industries_location[activitat_ubicacio+' '+nom_abocament]['x'], industries_location[activitat_ubicacio+' '+nom_abocament]['y'], 1))

                else:   #No passa per depuradora
                    self.add_industry_to_river(industries_to_river, industry)
                    ind_origen.add((industries_location[activitat_ubicacio+' '+nom_abocament]['x'], industries_location[activitat_ubicacio+' '+nom_abocament]['y'], 2))
                    n_2.add((industries_location[activitat_ubicacio+' '+nom_abocament]['x'], industries_location[activitat_ubicacio+' '+nom_abocament]['y'], 1))

            else:    #No passa per depuradora
                self.add_industry_to_river(industries_to_river, industry)
                ind_origen.add((industries_location[activitat_ubicacio + ' ' + nom_abocament]['x'],
                                    industries_location[activitat_ubicacio + ' ' + nom_abocament]['y'], 3))
                n_3.add((industries_location[activitat_ubicacio + ' ' + nom_abocament]['x'],
                         industries_location[activitat_ubicacio + ' ' + nom_abocament]['y'], 1))

        df = pd.DataFrame(ind_origen, columns=['x', 'y', 'origen'])
        df_2 = pd.DataFrame(ind_code, columns=['x', 'y', 'ccae'])
        print(len(n_1), len(n_2), len(n_3))
        df.to_csv("industries_origen.csv")
        df_2.to_csv("industries_ccae.csv")

        return industries_to_edar, industries_to_river






