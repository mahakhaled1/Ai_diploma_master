def perfect(num):
    """
    Check perfect number.
 
    Args:
        num: Number.
    """
 
    sum = 0
 
    for i in range(1, num):
        if num % i == 0:
            sum += i
 
    if sum == num:
        return True
    else:
        return False
 
 
def allPerfect(start, end):
    """
    Print perfect numbers.
 
    Args:
        start: First number.
        end: Last number.
    """
 
    for i in range(start, end + 1):
        if perfect(i):
            print(i)
 
 
allPerfect(1, 100)