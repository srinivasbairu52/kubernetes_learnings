from flask import Flask, render_template, request, redirect
from database import (
    get_all_customers,
    get_customer_by_id,
    add_customer
)

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/customers")
def customers():
    customer_list = get_all_customers()
    return render_template(
        "customers.html",
        customers=customer_list
    )


@app.route("/customer/<int:customer_id>")
def customer_details(customer_id):
    customer = get_customer_by_id(customer_id)

    return render_template(
        "customer_details.html",
        customer=customer
    )


@app.route("/add-customer", methods=["GET", "POST"])
def add_customer_page():

    if request.method == "POST":

        add_customer(
            request.form["account_number"],
            request.form["first_name"],
            request.form["last_name"],
            request.form["account_type"],
            request.form["balance"],
            request.form["phone"],
            request.form["email"],
            request.form["address"],
            request.form["branch"]
        )

        return redirect("/customers")

    return render_template("add_customer.html")


if __name__ == "__main__":
    app.run(debug=True)