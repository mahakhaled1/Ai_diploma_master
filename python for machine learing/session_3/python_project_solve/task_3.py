def factors(num):
    """
    Print prime factors.
 
    Args:
        num: Number.
    """
 
    i = 2
 
    while num > 1:
        if num % i == 0:
            print(i)
            num = num // i
        else:
            i += 1
 
 
x = int(input("Enter number: "))
factors(x)