distance = int(input("Enter the distance (in km): "))
if 1 <= distance <= 50:
    fare = distance * 8
elif 51 <= distance <= 100:
    fare = (50 * 8) + ((distance - 50) * 10)
elif distance > 100:
    fare = (50 * 8) + (50 * 10) + ((distance - 100) * 12)
else:
    fare = 0
print(f"The total fare is Rs. {fare}.")