import platform

if platform.system() == "Windows":
    import pymysql

    pymysql.install_as_MySQLdb()
    # Django 6.x checks mysqlclient version_info; align for PyMySQL on Windows.
    pymysql.version_info = (2, 2, 1)
    pymysql.__version__ = "2.2.1"
else:
    try:
        import MySQLdb  # noqa: F401
    except ImportError:
        import pymysql

        pymysql.install_as_MySQLdb()
