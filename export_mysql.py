import os
import sqlite3
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql
from flask import Flask
from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mobix.db'
db.init_app(app)

output_file = 'mobix_database.sql'

with app.app_context():
    sqlite_conn = sqlite3.connect('mobix.db')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    sql_statements = []
    sql_statements.append("-- MOBIX Mobile Shop Management System")
    sql_statements.append("-- MySQL / MariaDB Database Dump for phpMyAdmin")
    sql_statements.append("-- Compatible with MySQL 5.7+, MySQL 8.0+, and MariaDB 10.x+")
    sql_statements.append("")
    sql_statements.append("SET FOREIGN_KEY_CHECKS = 0;")
    sql_statements.append("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';")
    sql_statements.append("SET NAMES utf8mb4;")
    sql_statements.append("")

    # Generate CREATE TABLE statements for all SQLAlchemy models
    for table in db.metadata.sorted_tables:
        sql_statements.append(f"-- Table structure for `{table.name}`")
        sql_statements.append(f"DROP TABLE IF EXISTS `{table.name}`;")
        ddl = str(CreateTable(table).compile(dialect=mysql.dialect())).strip()
        if not ddl.endswith(';'):
            ddl += ';'
        sql_statements.append(ddl)
        sql_statements.append("")

    # Populate data from mobix.db if table exists
    for table in db.metadata.sorted_tables:
        try:
            sqlite_cur.execute(f"SELECT * FROM `{table.name}`")
            rows = sqlite_cur.fetchall()
            if rows:
                col_names = [f"`{col}`" for col in rows[0].keys()]
                sql_statements.append(f"-- Dumping data for table `{table.name}`")
                for row in rows:
                    vals = []
                    for val in row:
                        if val is None:
                            vals.append("NULL")
                        elif isinstance(val, (int, float)):
                            vals.append(str(val))
                        elif isinstance(val, bool):
                            vals.append("1" if val else "0")
                        else:
                            # Escape string for MySQL
                            escaped = str(val).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
                            vals.append(f"'{escaped}'")
                    sql_statements.append(f"INSERT INTO `{table.name}` ({', '.join(col_names)}) VALUES ({', '.join(vals)});")
                sql_statements.append("")
        except Exception as e:
            # Table might not exist in sqlite
            pass

    sql_statements.append("SET FOREIGN_KEY_CHECKS = 1;")
    sql_statements.append("")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_statements))

    print(f"Successfully generated {output_file} ({len(sql_statements)} lines)")
