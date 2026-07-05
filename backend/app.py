from flask import Flask, render_template
from database import get_all_customers, get_customer_by_id

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

if __name__ == "__main__":
    app.run(debug=True)