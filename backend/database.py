import mysql.connector
from config import DB_CONFIG


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def get_all_customers():
    connection = get_connection()

    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM customer")

    customers = cursor.fetchall()

    cursor.close()
    connection.close()

    return customers


def get_customer_by_id(customer_id):
    connection = get_connection()

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM customer WHERE customer_id = %s",
        (customer_id,)
    )

    customer = cursor.fetchone()

    cursor.close()
    connection.close()

    return customer


def add_customer(
    account_number,
    first_name,
    last_name,
    account_type,
    balance,
    phone,
    email,
    address,
    branch
):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO customer
        (
            account_number,
            first_name,
            last_name,
            account_type,
            balance,
            phone,
            email,
            address,
            branch
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            account_number,
            first_name,
            last_name,
            account_type,
            balance,
            phone,
            email,
            address,
            branch
        )
    )

    connection.commit()

    cursor.close()
    connection.close()