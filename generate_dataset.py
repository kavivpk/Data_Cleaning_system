
import pandas as pd

data = {
    "Order_ID": [101, 102, 103, 104, 105, 105, 107, 108, 109, 110],
    "Customer_Name": [
        "Arun", "Ravi", "Kumar", None, "Priya",
        "Priya", "Suresh", "Manoj", "Divya", "Karthik"
    ],
    "Email": [
        "arun@gmail.com", "ravi@gmail.com", "kumar@gmail.com",
        "invalid-email", "priya@gmail.com", "priya@gmail.com",
        None, "manoj@gmail.com", "divya@gmail.com", "karthik@gmail.com"
    ],
    "Product": [
        "Laptop", "Mobile", "Keyboard", "Mouse", "Laptop",
        "Laptop", "Mobile", "MOUSE", "Keyboard", "Laptop"
    ],
    "Quantity": [1, 2, 1, 3, 1, 1, -2, 2, 1, 1],
    "Price": [45000, 15000, 1200, 500, 45000, 45000, 15000, 500, None, 45000],
    "City": [
        "Chennai", "chennai", "MADURAI", "Trichy", "Madurai",
        "Madurai", "Trichy", None, "CHENNAI", "Coimbatore"
    ],
    "Order_Date": [
        "2026-01-01", "02/01/2026", "2026-01-03",
        "04-01-2026", "2026-01-05", "2026-01-05",
        "2026/01/07", "08-01-2026", "2026-01-09", "10/01/2026"
    ]
}

df = pd.DataFrame(data)

df.to_csv("data/raw/sales_dirty.csv", index=False)

print("Dataset created successfully!")
print(df)

