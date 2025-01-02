product_code = int(input("Enter product code (1: Battery, 2: Key-based, 3: Electrical): "))
order_amount = float(input("Enter the order amount: "))
if product_code == 1 and order_amount > 1000:
    discount = order_amount * 0.10
elif product_code == 2 and order_amount > 100:
    discount = order_amount * 0.05
elif product_code == 3 and order_amount > 500:
    discount = order_amount * 0.10
else:
    discount = 0
net_amount = order_amount - discount
print(f"The net amount to be paid is Rs. {net_amount:.2f}.")