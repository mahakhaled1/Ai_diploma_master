def binary(num):
    """
    Convert decimal to binary.
 
    Args:
        num: Decimal number.
    """
 
    if num == 0:
        print(0)
        return
 
    b = ""
 
    while num > 0:
        b = str(num % 2) + b
        num = num // 2
 
    print(b)
 
 
x = int(input("Enter number: "))
binary(x)