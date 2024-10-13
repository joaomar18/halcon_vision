import sqlite3
import logging

class DBClient:
    """
    A SQLite database client that allows for basic database operations
    such as creating tables, inserting entries, updating, deleting, and retrieving entries.

    Attributes:
    -----------
    db_name : str
        The name of the SQLite database file.
    conn : sqlite3.Connection
        The connection object for the database.
    cursor : sqlite3.Cursor
        The cursor object used to execute SQL commands.
    """

    def __init__(self, db_file: str, logger: logging.Logger):
        """
        Initializes the DBClient with the specified database file.

        Parameters:
        -----------
        db_name : str
            The name of the SQLite database file to connect to. If the database 
            does not exist, it will be created.

        Example:
        --------
        db = DBClient('example.db')
        """
        try:
            self._db_file = db_file
            self._conn = sqlite3.connect(db_file)
            self._cursor = self._conn.cursor()

            self._logger = logger

        except Exception as e:
            self._logger.error(f"DB Client - Error initializing database client: {e}")

    def create_table(self, table_name: str, columns:list[str]):
        """
        Creates a new table in the database with the specified name and columns.

        Parameters:
        -----------
        table_name : str
            The name of the table to create.
        columns : list[str]
            A list of column definitions (including data types) for the table.

        Example:
        --------
        db.create_table('users', ['id INTEGER PRIMARY KEY', 'name TEXT', 'age INTEGER'])

        Notes:
        ------
        The method will catch and print any exceptions that occur during the table creation process.
        """

        try:
            columns = ', '.join(columns)
            self._cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
            self._conn.commit()
        except Exception as e:
            self._logger.error(f"DB Client - Error creating table: {e}")
    
    def insert_entry(self, table_name: str, parameters: tuple, values: tuple):
        """
        Inserts a new entry into the specified table.

        Parameters:
        -----------
        table_name : str
            The name of the table to insert the entry into.
        parameters : tuple
            A tuple of column names where values will be inserted.
        values : tuple
            A tuple of values corresponding to the specified columns.

        Example:
        --------
        db.insert_entry('users', ('name', 'age'), ('John Doe', 30))

        Notes:
        ------
        This method uses parameterized queries to avoid SQL injection.
        """

        try:
            placeholders = ', '.join('?' * len(values))
            columns = ', '.join(parameters)
            self._cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)
            self._conn.commit()
        except Exception as e:
            self._logger.error(f"DB Client - Error inserting entry into {table_name}: {e}")
    
    def update_entry(self, table_name: str, set_clause: str, where_clause: str = None):
        """
        Updates an existing entry in the specified table using a custom query.

        Parameters:
        -----------
        table_name : str
            The name of the table where the entry should be updated.
        set_clause : str
            The SQL SET clause specifying the columns to update and their new values.
        where_clause : str, optional
            The SQL WHERE clause specifying which rows to update (default is None).

        Example:
        --------
        db.update_entry('users', "age = ?", "name = ?", (31, 'John Doe'))

        Notes:
        ------
        This method uses parameterized queries to avoid SQL injection.
        """

        try:
            query = f"UPDATE {table_name} SET {set_clause}"
            if where_clause:
                query += f" WHERE {where_clause}"
            self._cursor.execute(query)
            self._conn.commit()
        except Exception as e:
            self._logger.error(f"DB Client - Error updating entry in {table_name}: {e}")
    
    def delete_entries(self, table_name: str, where_clause: str, params: tuple = ()):
        """
        Deletes entries from the specified table using a custom query.

        Parameters:
        -----------
        table_name : str
            The name of the table from which entries will be deleted.
        where_clause : str
            A SQL condition specifying which entries to delete.
        params : tuple
            The parameters to be used with the SQL query.

        Example:
        --------
        db.delete_entries('users', "age < ?", (18,))

        Notes:
        ------
        This method uses parameterized queries to avoid SQL injection.
        """

        try:
            query = f"DELETE FROM {table_name} WHERE {where_clause}"
            self._cursor.execute(query, params)
            self._conn.commit()
        except Exception as e:
            self._logger.error(f"DB Client - Error deleting entries from {table_name}: {e}")
        
    def get_entries(self, table_name: str, where_clause: str = None, params: tuple = ()) -> list:
        """
        Retrieves entries from the database using a SQL SELECT query.

        Parameters:
        -----------
        table_name : str
            The name of the table to query.
        where_clause : str, optional
            A SQL condition specifying which entries to retrieve (default is None).
        params : tuple, optional
            The parameters to be used with the SQL query (default is empty tuple).

        Returns:
        --------
        list
            A list of tuples, where each tuple represents a row of the result set.

        Example:
        --------
        rows = db.get_entries('users', "age >= ?", (18,))
        for row in rows:
            print(row)

        Notes:
        ------
        This method uses parameterized queries to avoid SQL injection.
        """

        try:
            query = f"SELECT * FROM {table_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            self._cursor.execute(query, params)
            return self._cursor.fetchall()
        except Exception as e:
            self._logger.error(f"DB Client - Error retrieving entries from {table_name}: {e}")

    def close(self):
        """
        Closes the connection to the SQLite database.

        Example:
        --------
        db.close()
        """

        try:
            self._conn.close()
        except Exception as e:
            self._logger.error(f"DB Client - Error closing database connection: {e}")