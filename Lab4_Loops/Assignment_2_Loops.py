num = int ( input( "Enter any number: "))
original_num = num
rev=0
while num > 0:
    rem = num%10
    rev = rev*10 + rem
    num = num//10
if original_num==rev :
    print(original_num, "is a Palindrome")
else :
    print(original_num, "is not a Palindrome")