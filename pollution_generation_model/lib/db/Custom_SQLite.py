import sqlite3
from sqlite3 import Error


class Custom_SQLite:

    def __init__(self, url):
        self.url = url

    def create_connection(self):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(self.url)
            self.__init_db(conn)
            print(sqlite3.version)
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()

    def getConfigurations(self):
        conn = None
        data = []

        try:
            conn = sqlite3.connect(self.url)
            print(conn.execute("SELECT * FROM config").fetchall())
            for c in conn.execute("SELECT * FROM config").fetchall():
                conf = Config(c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10])
                data.append(conf)
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()
            return data

    def __init_db(self, connection):
        self.__crate_tables(connection)

    def __crate_tables(self, connection):
        """ Create al the table need in my config database """
        connection.execute(''' CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name,
            postgre_dbname,
            postgre_user,
            postgre_url,
            postgre_pass,
            eu_db,
            dp_pop_db,
            wwtp_con_db,
            comp_con_db) ''')

        print("Custom db correctly initialized :)")

        connection.commit()

    def create_config(self, name):
        sql = '''
            INSERT INTO config (config_name) VALUES (?)
        '''
        conn = None
        try:
            conn = sqlite3.connect(self.url)
            conn.execute(sql, [name])
            conn.commit()
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()

    def duplicate_config(self, name, url, dbname, user, password):

        new_name = str(name) + "_1"
        sql = '''
                INSERT INTO config (
                    config_name,
                    postgre_dbname ,
                    postgre_url ,
                    postgre_user ,
                    postgre_pass) VALUES (?,?,?,?,?)
                '''
        conn = None
        try:
            conn = sqlite3.connect(self.url)
            conn.execute(sql, (new_name, dbname, url, user, password))
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()

    def rename_config(self, name, config_id):
        sql = '''
            UPDATE config
            SET config_name = ?
            WHERE id = ?
        '''

        conn = None
        try:
            conn = sqlite3.connect(self.url)
            conn.execute(sql, [name, config_id])
            conn.commit()
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()

        print("Data Saved!")

    def update_config_data(self, id_config, url, dbname, user, password, eu_db, dp_pop_db, wwtp_con_db, comp_con_db):

        sql = '''
                UPDATE config
                SET postgre_dbname = ? ,
                    postgre_url = ? ,
                    postgre_user = ? ,
                    postgre_pass = ? ,
                    eu_db = ? ,
                    dp_pop_db = ? ,
                    wwtp_con_db = ? ,
                    comp_con_db = ? 
                WHERE id = ?
            '''

        try:
            conn = sqlite3.connect(self.url)
            conn.execute(sql, [dbname, url, user, password, eu_db, dp_pop_db, wwtp_con_db, comp_con_db, id_config])
            conn.commit()
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()

        print("Data Saved!")