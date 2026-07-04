USE bankdb;

INSERT INTO customer
(account_number,
first_name,
last_name,
account_type,
balance,
phone,
email,
address,
branch)

VALUES
('ACC100001','Rahul','Sharma','Savings',15000.00,'9876543210','rahul@gmail.com','Hyderabad','Ameerpet'),

('ACC100002','Anjali','Reddy','Savings',54000.50,'9876543211','anjali@gmail.com','Warangal','Hanamkonda'),

('ACC100003','Ravi','Kumar','Current',120000.75,'9876543212','ravi@gmail.com','Bangalore','Whitefield'),

('ACC100004','Sneha','Patel','Savings',8000.25,'9876543213','sneha@gmail.com','Chennai','T Nagar'),

('ACC100005','Arjun','Verma','Current',350000.00,'9876543214','arjun@gmail.com','Mumbai','Andheri');