from database import get_all_customers

customers = get_all_customers()

for customer in customers:
    print(customer)