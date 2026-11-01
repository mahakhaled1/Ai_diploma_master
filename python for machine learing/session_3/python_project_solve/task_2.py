def prime(num):
    """
    Check prime number.
 
    Args:
        num: Number.
 
    Returns:
        True or False.
    """
 
    if num < 2:
        return False
 
    for i in range(2, num):
        if num % i == 0:
            return False
 
    return True
 
 
def twin():
   
 
    for i in range(2, 1000):
        if prime(i) and prime(i + 2):
            print(i, i + 2)
 
 
twin()
 