import sys
import time
import socket
import logging
import pyodbc
import traceback
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sql_connection_diagnostic.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Connection parameters - replace with your values
SERVER = 'your_server_name_or_ip'  # e.g., 'localhost' or '192.168.1.100'
DATABASE = 'your_database_name'    # e.g., 'master'
USERNAME = 'your_username'         # e.g., 'sa'
PASSWORD = 'your_password'
PORT = '1433'                      # Default SQL Server port
DRIVER = 'ODBC Driver 17 for SQL Server'

# Test timeout values (in seconds)
TIMEOUTS = [5, 15, 30, 60, 120]

def check_port_open(host, port, timeout=3):
    """Check if the specified port is open on the host."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking port {port} on {host}: {e}")
        return False

def test_connection_string(conn_str, timeout=30):
    """Test a connection string with a specific timeout."""
    start_time = time.time()
    try:
        logger.info(f"Testing connection with timeout {timeout}s: {conn_str}")
        with pyodbc.connect(conn_str, timeout=timeout) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            elapsed = time.time() - start_time
            logger.info(f"Connection successful! ({elapsed:.2f}s)")
            logger.info(f"SQL Server version: {version}")
            return True, elapsed, version
    except Exception as e:
        elapsed = time.time() - start_time
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"Connection failed after {elapsed:.2f}s: {error_type}: {error_msg}")
        return False, elapsed, error_type + ": " + error_msg

def test_trusted_connection():
    """Test Windows Authentication (trusted connection)."""
    conn_str = f"DRIVER={{{DRIVER}}};SERVER={SERVER},{PORT};DATABASE={DATABASE};Trusted_Connection=yes;"
    return test_connection_string(conn_str)

def test_sql_auth_connection():
    """Test SQL Server Authentication."""
    conn_str = f"DRIVER={{{DRIVER}}};SERVER={SERVER},{PORT};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};"
    return test_connection_string(conn_str)

def test_connection_with_timeouts():
    """Test connections with various timeout values."""
    results = []
    
    for timeout in TIMEOUTS:
        conn_str = f"DRIVER={{{DRIVER}}};SERVER={SERVER},{PORT};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        success, elapsed, message = test_connection_string(conn_str, timeout)
        results.append({
            "timeout": timeout,
            "success": success,
            "elapsed": elapsed,
            "message": message
        })
        if success:
            break
    
    return results

def test_connection_without_port():
    """Test connection without explicitly specifying port."""
    conn_str = f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};"
    return test_connection_string(conn_str)

def test_connection_with_instance():
    """Test connection with instance name instead of port."""
    # Replace INSTANCE_NAME with your SQL Server instance name if applicable
    instance_server = SERVER.split(',')[0] + '\\INSTANCE_NAME'
    conn_str = f"DRIVER={{{DRIVER}}};SERVER={instance_server};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};"
    return test_connection_string(conn_str)

def test_minimal_connection():
    """Test minimal connection to master database."""
    conn_str = f"DRIVER={{{DRIVER}}};SERVER={SERVER},{PORT};DATABASE=master;UID={USERNAME};PWD={PASSWORD};"
    return test_connection_string(conn_str)

def check_driver_availability():
    """Check if the specified ODBC driver is available."""
    available_drivers = pyodbc.drivers()
    logger.info("Available ODBC drivers:")
    for driver in available_drivers:
        logger.info(f"  - {driver}")
    
    driver_available = DRIVER in available_drivers
    if driver_available:
        logger.info(f"Driver '{DRIVER}' is available.")
    else:
        logger.error(f"Driver '{DRIVER}' is NOT available!")
        logger.info("Consider using one of the available drivers listed above.")
    
    return driver_available, available_drivers

def run_diagnostics():
    """Run comprehensive connection diagnostics."""
    logger.info("=" * 80)
    logger.info(f"Starting SQL Server connection diagnostics at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PyODBC version: {pyodbc.version}")
    logger.info("-" * 80)
    
    # Check connectivity to the server
    logger.info(f"Checking if server {SERVER} is reachable...")
    host = SERVER.split(',')[0]  # Extract hostname/IP from SERVER,PORT format
    if host.lower() in ('localhost', '127.0.0.1', '::1'):
        logger.info(f"Server is localhost, skipping ping test.")
        host_reachable = True
    else:
        try:
            # Simple ping test using socket
            host_ip = socket.gethostbyname(host)
            logger.info(f"Resolved {host} to IP: {host_ip}")
            
            response = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            response.settimeout(5)
            response.connect((host_ip, 1))  # Just testing connectivity, not the actual port
            host_reachable = True
            logger.info(f"Host {host} ({host_ip}) is reachable.")
        except socket.error as e:
            host_reachable = False
            logger.error(f"Host {host} is not reachable: {e}")
    
    # Check if the specified port is open
    if host_reachable:
        logger.info(f"Checking if port {PORT} is open on {host}...")
        port_open = check_port_open(host, PORT)
        if port_open:
            logger.info(f"Port {PORT} is open on {host}.")
        else:
            logger.warning(f"Port {PORT} is NOT open on {host}!")
    
    # Check driver availability
    logger.info("-" * 80)
    driver_available, available_drivers = check_driver_availability()
    
    if not driver_available:
        alternative_drivers = [d for d in available_drivers if 'sql server' in d.lower()]
        if alternative_drivers:
            logger.info(f"You might want to try these alternative SQL Server drivers:")
            for alt_driver in alternative_drivers:
                logger.info(f"  - {alt_driver}")
    
    # Only proceed with connection tests if all prerequisites are met
    if not (host_reachable and driver_available):
        logger.error("Cannot proceed with connection tests due to prerequisites not being met.")
        return
    
    # Run connection tests
    logger.info("-" * 80)
    logger.info("Testing SQL Server Authentication connection...")
    sql_auth_success, sql_auth_time, sql_auth_msg = test_sql_auth_connection()
    
    logger.info("-" * 80)
    logger.info("Testing Windows Authentication connection...")
    win_auth_success, win_auth_time, win_auth_msg = test_trusted_connection()
    
    logger.info("-" * 80)
    logger.info("Testing connection without explicit port...")
    no_port_success, no_port_time, no_port_msg = test_connection_without_port()
    
    logger.info("-" * 80)
    logger.info("Testing minimal connection to master database...")
    min_conn_success, min_conn_time, min_conn_msg = test_minimal_connection()
    
    logger.info("-" * 80)
    logger.info("Testing connection with different timeout values...")
    timeout_results = test_connection_with_timeouts()
    
    # Summary
    logger.info("=" * 80)
    logger.info("DIAGNOSIS SUMMARY:")
    logger.info("-" * 80)
    logger.info(f"Host reachable: {host_reachable}")
    if host_reachable:
        logger.info(f"Port {PORT} open: {port_open}")
    logger.info(f"Driver '{DRIVER}' available: {driver_available}")
    logger.info(f"SQL Auth connection: {'SUCCESS' if sql_auth_success else 'FAILED'}")
    logger.info(f"Windows Auth connection: {'SUCCESS' if win_auth_success else 'FAILED'}")
    logger.info(f"No-port connection: {'SUCCESS' if no_port_success else 'FAILED'}")
    logger.info(f"Minimal connection: {'SUCCESS' if min_conn_success else 'FAILED'}")
    
    # Provide recommendations based on diagnosis
    logger.info("-" * 80)
    logger.info("RECOMMENDATIONS:")
    
    if not host_reachable:
        logger.info("1. Verify the server hostname/IP address.")
        logger.info("2. Check network connectivity to the server.")
        logger.info("3. Ensure there are no firewall rules blocking access.")
    elif not port_open:
        logger.info("1. Verify SQL Server is running on the specified port.")
        logger.info("2. Check firewall rules allow access to this port.")
        logger.info("3. Verify SQL Server is configured to allow remote connections.")
        logger.info("4. Ensure TCP/IP protocol is enabled in SQL Server Configuration Manager.")
    elif not sql_auth_success and not win_auth_success:
        logger.info("1. Verify username and password.")
        logger.info("2. Check SQL Server is configured for the authentication mode you're using.")
        logger.info("3. Verify the user has permission to access the server and database.")
    elif min_conn_success and not sql_auth_success:
        logger.info("1. Check that the specified database exists.")
        logger.info("2. Verify the user has permission to access that specific database.")
    elif not any(result["success"] for result in timeout_results):
        logger.info("1. Increase the connection timeout value in your application.")
        logger.info("2. Check for performance issues on the SQL Server.")
        logger.info("3. Review SQL Server logs for resource constraints or blocking issues.")
    else:
        logger.info("1. Review specific error messages from the tests above.")
        logger.info("2. Check your connection string parameters.")
        logger.info("3. Verify SQL Server configurations related to connections.")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    try:
        run_diagnostics()
    except Exception as e:
        logger.error(f"Diagnostic script encountered an error: {e}")
        logger.error(traceback.format_exc())