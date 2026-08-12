import json
import logging
import os
import time

from flask import Flask, request, jsonify, g
from flask_cors import CORS

import mysql.connector
import boto3
from botocore.exceptions import ClientError


#########################################################
# Flask App
#########################################################

app = Flask(__name__)
CORS(app)


#########################################################
# Logging Configuration
#########################################################

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("/var/log/app/app.log"),
        logging.StreamHandler()
    ]
)


#########################################################
# Request Logging
#########################################################

@app.before_request
def before_request():

    g.start_time = time.time()

    app.logger.info("=" * 80)
    app.logger.info(f"Method      : {request.method}")
    app.logger.info(f"URL         : {request.url}")
    app.logger.info(f"Client IP   : {request.remote_addr}")

    # Don't log sensitive request data
    if request.is_json:

        data = request.get_json(silent=True)

        if data:
            safe_data = data.copy()

            # Hide sensitive fields
            for field in [
                "password",
                "token",
                "secret",
                "access_token"
            ]:
                if field in safe_data:
                    safe_data[field] = "***"

            app.logger.info(f"Request JSON: {safe_data}")

    elif request.form:
        app.logger.info(
            f"Request Form: {request.form.to_dict()}"
        )


#########################################################
# Response Logging
#########################################################

@app.after_request
def after_request(response):

    duration = time.time() - g.start_time

    app.logger.info(
        f"Status Code : {response.status_code}"
    )

    app.logger.info(
        f"Response Time : {duration:.3f} seconds"
    )

    app.logger.info("=" * 80)

    return response


#########################################################
# Global Error Handler
#########################################################

@app.errorhandler(Exception)
def handle_exception(e):

    app.logger.exception(
        "Unhandled Exception:"
    )

    return jsonify({
        "error": "Internal server error"
    }), 500


#########################################################
# AWS Configuration
#########################################################

AWS_REGION = os.environ.get(
    "AWS_REGION",
    "us-east-1"
)

SECRET_NAME = os.environ.get(
    "SECRET_NAME",
    "rds!db-ac74596e-50e0-4120-8858-461f7beef0fe"
)


#########################################################
# Secrets Manager
#########################################################

def get_secret():

    try:

        app.logger.info(
            "Reading database credentials from Secrets Manager"
        )

        # No access key / secret key required.
        #
        # boto3 automatically gets temporary credentials
        # from EKS Pod Identity.

        client = boto3.client(
            "secretsmanager",
            region_name=AWS_REGION
        )

        response = client.get_secret_value(
            SecretId=SECRET_NAME
        )

        secret_string = response.get(
            "SecretString"
        )

        if secret_string:

            return json.loads(secret_string)

        # Handle binary secret
        secret_binary = response.get(
            "SecretBinary"
        )

        if secret_binary:

            return json.loads(
                secret_binary.decode("utf-8")
            )

        raise Exception(
            "SecretString and SecretBinary are empty"
        )

    except ClientError as e:

        app.logger.error(
            f"Secrets Manager error: {e}"
        )

        raise

    except Exception as e:

        app.logger.error(
            f"Secret retrieval failed: {e}"
        )

        raise


#########################################################
# Load Database Credentials
#########################################################

try:

    secret_data = get_secret()

    app.logger.info(
        "Database secret retrieved successfully"
    )

except Exception:

    app.logger.exception(
        "Failed to retrieve database secret"
    )

    raise


#########################################################
# RDS Configuration
#########################################################

DB_HOST = os.environ.get(
    "DB_HOST"
)

DB_PORT = int(
    os.environ.get(
        "DB_PORT",
        "3306"
    )
)

DB_NAME = os.environ.get(
    "DB_NAME",
    "dev"
)


db_config = {
    "host": DB_HOST,
    "port": DB_PORT,
    "user": secret_data["username"],
    "password": secret_data["password"],
    "database": DB_NAME
}


#########################################################
# Database Connection
#########################################################

def get_db_connection():

    try:

        connection = mysql.connector.connect(
            **db_config
        )

        return connection

    except mysql.connector.Error as err:

        app.logger.error(
            f"Database connection failed: {err}"
        )

        raise


#########################################################
# Health Check
#########################################################

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "healthy"
    })


#########################################################
# Database Health Check
#########################################################

@app.route("/db-health", methods=["GET"])
def db_health():

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1"
        )

        result = cursor.fetchone()

        return jsonify({
            "status": "healthy",
            "database": "connected",
            "result": result[0]
        })

    except Exception as e:

        app.logger.exception(
            "Database health check failed"
        )

        return jsonify({
            "status": "unhealthy",
            "database": "disconnected"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


#########################################################
# Home
#########################################################

@app.route("/")
def home():

    return "Hello from EKS Flask Backend"


#########################################################
# Get All Users
#########################################################

@app.route("/users", methods=["GET"])
def get_users():

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            "SELECT * FROM users"
        )

        users = cursor.fetchall()

        return jsonify(users)

    except mysql.connector.Error as err:

        app.logger.error(
            f"Get users error: {err}"
        )

        return jsonify({
            "error": "Database error"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


#########################################################
# Get User By ID
#########################################################

@app.route(
    "/users/<int:user_id>",
    methods=["GET"]
)
def get_user(user_id):

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            "SELECT * FROM users WHERE id=%s",
            (user_id,)
        )

        user = cursor.fetchone()

        if user:

            return jsonify(user)

        return jsonify({
            "error": "User not found"
        }), 404

    except mysql.connector.Error as err:

        app.logger.error(
            f"Get user error: {err}"
        )

        return jsonify({
            "error": "Database error"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


#########################################################
# Add User
#########################################################

@app.route(
    "/users/add",
    methods=["POST"]
)
def add_user():

    conn = None
    cursor = None

    data = request.get_json(
        silent=True
    ) or {}

    name = data.get("name")
    email = data.get("email")

    if not name or not email:

        return jsonify({
            "error": "Name and Email are required"
        }), 400

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users(name, email)
            VALUES(%s, %s)
            """,
            (name, email)
        )

        conn.commit()

        app.logger.info(
            f"Inserted User: {name}"
        )

        return jsonify({
            "message": "User added successfully"
        }), 201

    except mysql.connector.Error as err:

        if conn:
            conn.rollback()

        app.logger.error(
            f"Insert user error: {err}"
        )

        return jsonify({
            "error": "Database error"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


#########################################################
# Update User
#########################################################

@app.route(
    "/users/update/<int:user_id>",
    methods=["PUT"]
)
def update_user(user_id):

    conn = None
    cursor = None

    data = request.get_json(
        silent=True
    ) or {}

    name = data.get("name")
    email = data.get("email")

    if not name or not email:

        return jsonify({
            "error": "Name and Email are required"
        }), 400

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE id=%s",
            (user_id,)
        )

        if not cursor.fetchone():

            return jsonify({
                "error": "User not found"
            }), 404

        cursor.execute(
            """
            UPDATE users
            SET name=%s, email=%s
            WHERE id=%s
            """,
            (name, email, user_id)
        )

        conn.commit()

        app.logger.info(
            f"Updated User: {user_id}"
        )

        return jsonify({
            "message": "User updated successfully"
        })

    except mysql.connector.Error as err:

        if conn:
            conn.rollback()

        app.logger.error(
            f"Update user error: {err}"
        )

        return jsonify({
            "error": "Database error"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


#########################################################
# Delete User
#########################################################

@app.route(
    "/users/delete/<int:user_id>",
    methods=["DELETE"]
)
def delete_user(user_id):

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE id=%s",
            (user_id,)
        )

        if not cursor.fetchone():

            return jsonify({
                "error": "User not found"
            }), 404

        cursor.execute(
            "DELETE FROM users WHERE id=%s",
            (user_id,)
        )

        conn.commit()

        app.logger.info(
            f"Deleted User: {user_id}"
        )

        return jsonify({
            "message": "User deleted successfully"
        })

    except mysql.connector.Error as err:

        if conn:
            conn.rollback()

        app.logger.error(
            f"Delete user error: {err}"
        )

        return jsonify({
            "error": "Database error"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


#########################################################
# Start Server
#########################################################

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
