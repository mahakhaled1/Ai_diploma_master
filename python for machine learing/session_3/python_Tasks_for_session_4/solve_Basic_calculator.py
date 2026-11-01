def add(x, y):
    """
    Add two numbers.

    :param x: First number
    :param y: Second number
    :return: Sum
    """
    return x + y


def subtract(x, y):
    """
    Subtract two numbers.

    :param x: First number
    :param y: Second number
    :return: Difference
    """
    return x - y


def multiply(x, y):
    """
    Multiply two numbers.

    :param x: First number
    :param y: Second number
    :return: Product
    """
    return x * y


def divide(x, y):
    """
    Divide two numbers.

    :param x: First number
    :param y: Second number
    :return: Division
    """
    if y == 0:
        return "Cannot divide by zero!"
    return x / y


while True:

    print("1. Addition")
    print("2. Subtraction")
    print("3. Multiplication")
    print("4. Division")
    print("5. Exit")

    choice = input("Choose: ")

    if choice == "5":
        print("Thank you!")
        break

    try:
        num1 = float(input("Enter first number: "))
        num2 = float(input("Enter second number: "))
    except:
        print("Invalid input!")
        continue

    if choice == "1":
        print("The result is:", add(num1, num2))

    elif choice == "2":
        print("The result is:", subtract(num1, num2))

    elif choice == "3":
        print("The result is:", multiply(num1, num2))

    elif choice == "4":
        print("The result is:", divide(num1, num2))

    else:
        print("Invalid choice!")

    again = input("Another calculation? (yes/no): ")

    if again.lower() != "yes":
        print("Thank you!")
        break