
## Install Dependencies

Make sure you have the necessary dependencies installed:

`pip install pyodbc`

Update the connection parameters at the top of the script with your actual values:

```
SERVER: Your SQL Server hostname or IP address
DATABASE: The database you're trying to connect to
USERNAME and PASSWORD: Your SQL Server credentials
PORT: The port SQL Server is running on (default is 1433)
DRIVER: The ODBC driver name (default is 'ODBC Driver 17 for SQL Server')
```

Run the script:
`python sql_server_connection_diagnostic.py`

Review the output and the generated log file (sql_connection_diagnostic.log) for detailed diagnostics.

The script performs several diagnostics:

* Checks if the server is reachable
* Tests if the SQL Server port is open
* Verifies ODBC driver availability
* Attempts connections with different authentication methods
* Tests connections with various timeout values
* Provides specific recommendations based on the test results