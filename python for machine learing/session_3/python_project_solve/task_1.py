def table(num):
    """
    Print multiplication table.
 
    Args:
        num: Number.
    """
 
    for i in range(1, 11):
        print(num, "*", i, "=", num * i)
 
 
x = int(input("Enter number: "))
table(x)
 